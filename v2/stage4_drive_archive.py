"""Transfer the live encrypted archive through its private Google Drive file."""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


API = "https://www.googleapis.com"
NAME = "MADSC55-TV-V2 stage4-24 acceptance archive.enc"
FILE_ID_HASH = "9b99ee638e64a59d746fd62a2da64cde618649ddb6ba3b0dbb77c5032d816815"
MEDIA = "application/octet-stream"
FIELDS = "id,name,mimeType,trashed,size,sha256Checksum,version,headRevisionId,capabilities(canEdit,canDownload)"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def receipt_archive(directory):
    raw = (directory / "receipt.json").read_bytes()
    if sha256(raw) != os.environ["EXPECTED_RECEIPT"]:
        raise ValueError("Producer receipt SHA-256 mismatch")
    receipt = json.loads(raw)
    if receipt["run_id"] != os.environ["GITHUB_RUN_ID"]:
        raise ValueError("Receipt belongs to another Actions run")
    digest = receipt["archive"]["sha256"]
    size = receipt["archive_bytes"]
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or type(size) is not int or size <= 0:
        raise ValueError("Invalid archive digest or size")
    return digest, size


class DriveArchive:
    def __init__(self, token):
        if not token:
            raise ValueError("Google OIDC did not issue a Drive token")
        self.token = token

    def request(self, url, *, params=None, method="GET", data=None, headers=None):
        if params:
            url += "?" + urlencode(params)
        request = Request(url, data=data, headers=headers or {}, method=method)
        request.add_unredirected_header("Authorization", f"Bearer {self.token}")
        try:
            return urlopen(request, timeout=120)
        except HTTPError as exc:
            with exc:
                reason = re.search(rb'"reason"\s*:\s*"([A-Za-z]{1,64})"', exc.read(8192))
            detail = f" ({reason[1].decode()})" if reason else ""
            raise ValueError(f"Google Drive {method} returned HTTP {exc.code}{detail}") from None
        except URLError:
            raise ValueError(f"Google Drive {method} could not connect") from None

    def file(self, *, write=False):
        with self.request(f"{API}/drive/v3/files", params={
            "q": f"name = '{NAME}' and mimeType = '{MEDIA}' and trashed = false",
            "fields": f"files({FIELDS}),nextPageToken,incompleteSearch", "pageSize": 100,
        }) as response:
            listing = json.load(response)
        files = listing.get("files", [])
        if len(files) != 1 or listing.get("nextPageToken") or listing.get("incompleteSearch"):
            raise ValueError("Private Drive acceptance file is missing or ambiguous")
        file = files[0]
        file_id = file.get("id", "")
        if (not re.fullmatch(r"[A-Za-z0-9_-]+", file_id) or sha256(file_id.encode()) != FILE_ID_HASH
                or file.get("name") != NAME or file.get("mimeType") != MEDIA or file.get("trashed") is not False):
            raise ValueError("Private Drive acceptance file identity mismatch")
        capabilities = file.get("capabilities", {})
        if not capabilities.get("canDownload") or (write and not capabilities.get("canEdit")):
            raise ValueError("Insufficient access to the private Drive acceptance file")
        return file

    def revision(self, file_id, revision, size):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", revision):
            raise ValueError("Invalid Drive revision ID")
        url = f"{API}/drive/v3/files/{file_id}/revisions/{revision}"
        with self.request(url, params={"fields": "id,keepForever,size"}) as response:
            info = json.load(response)
        if info.get("id") != revision or info.get("keepForever") is not True or info.get("size") != str(size):
            raise ValueError("Drive revision is not pinned with the expected size")
        return url

    def publish(self, directory, digest, size):
        archive = directory / "inventory.enc"
        with archive.open("rb") as stream:
            if archive.stat().st_size != size or hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("Encrypted bytes differ from the producer receipt")
            file = self.file(write=True)
            file_id = file["id"]
            if file.get("sha256Checksum") != digest or file.get("size") != str(size):
                path = f"/upload/drive/v3/files/{file_id}"
                with self.request(API + path, method="PATCH", data=b"{}", params={
                    "uploadType": "resumable", "keepRevisionForever": "true", "fields": FIELDS,
                }, headers={"Content-Type": "application/json; charset=UTF-8",
                            "X-Upload-Content-Type": MEDIA, "X-Upload-Content-Length": str(size)}) as response:
                    session = response.headers.get("Location", "")
                location = urlsplit(session)
                if (location.scheme != "https" or location.netloc not in {"www.googleapis.com", "content.googleapis.com"}
                        or location.path not in {path, "/upload/drive/v3/files"}):
                    raise ValueError("Drive returned an unexpected upload session URL")
                stream.seek(0)
                with self.request(session, method="PUT", data=stream, headers={
                    "Content-Type": MEDIA, "Content-Length": str(size),
                }) as response:
                    file = json.load(response)
        if file.get("id") != file_id or file.get("size") != str(size) or file.get("sha256Checksum") != digest:
            raise ValueError("Drive write response differs from the sealed archive")
        version, revision = file.get("version", ""), file.get("headRevisionId", "")
        if not re.fullmatch(r"[1-9][0-9]*", version):
            raise ValueError("Drive did not return an archive version")
        self.revision(file_id, revision, size)
        return version, revision

    def download(self, directory, digest, size, revision):
        url = self.revision(self.file()["id"], revision, size)
        hasher = hashlib.sha256()
        received = 0
        with self.request(url, params={"alt": "media"}) as response, (directory / "inventory.enc").open("xb") as out:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > size:
                    raise ValueError("Drive revision exceeds the original archive size")
                hasher.update(chunk)
                out.write(chunk)
        if received != size or hasher.hexdigest() != digest:
            raise ValueError("Drive revision differs from the original archive")


def main():
    drive = DriveArchive(os.environ["STAGE4_DRIVE_TOKEN"])
    if sys.argv[1:] == ["preflight"]:
        drive.file(write=True)
        print("Verified the private Drive file identity and writer access")
        return
    mode, location = sys.argv[1:]
    directory = Path(location)
    digest, size = receipt_archive(directory)
    if mode == "publish":
        version, revision = drive.publish(directory, digest, size)
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as out:
            out.write(f"version={version}\nrevision={revision}\n")
        print(f"Verified and pinned encrypted Drive archive version {version}")
    elif mode == "download":
        drive.download(directory, digest, size, os.environ["STAGE4_DRIVE_REVISION"])
        print("Downloaded the pinned Drive revision and verified its size and SHA-256")
    else:
        raise ValueError("Invalid Drive archive command")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"Stage 4 Drive archive failed: {exc}") from None
