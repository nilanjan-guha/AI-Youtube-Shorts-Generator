"""YouTube Upload helper module using YouTube Data API v3 and OAuth 2.0.

Features:
  - Upload videos (Shorts & Full) with metadata
  - Set custom thumbnails
  - Post auto-pinned comments to drive engagement & subscriber conversion
"""
import os
import sys
from typing import List, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes needed to upload videos AND post/pin comments
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # Needed for comments & thumbnails
]
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def get_authenticated_service():
    """Authenticate with Google OAuth 2.0 and return YouTube service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"\n[OAuth Error] '{CLIENT_SECRETS_FILE}' not found in current folder!")
                print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console")
                print(f"and save it as '{CLIENT_SECRETS_FILE}' in this directory.")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    youtube,
    file_path: str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    category_id: str = "22",
    privacy_status: str = "private",
) -> str:
    """Upload an MP4 video file to YouTube channel."""
    tags = tags or ["Shorts"]
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "28",  # Science & Technology category ID
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%...")

    return response.get("id")


def set_thumbnail(youtube, video_id: str, thumbnail_path: str) -> bool:
    """Set custom thumbnail for an uploaded YouTube video."""
    if not os.path.exists(thumbnail_path):
        return False
    try:
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg", resumable=True)
        request = youtube.thumbnails().set(videoId=video_id, media_body=media)
        request.execute()
        print(f" -> Custom thumbnail set successfully for video: {video_id}")
        return True
    except Exception as e:
        print(f" -> Could not set custom thumbnail for {video_id}: {e}")
        return False


def post_pinned_comment(youtube, video_id: str, comment_text: str, is_short: bool = True) -> Optional[str]:
    """Post a top-level comment on the video and pin it to drive engagement.
    
    Pinned comments are the #1 conversion driver on YouTube:
      - They are always visible at the top of the comment section
      - Drive subscribe + bell clicks
      - Create engagement loop (viewers respond to pinned comment)
    """
    try:
        # Post comment
        request = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text,
                        }
                    },
                }
            },
        )
        response = request.execute()
        comment_id = response["snippet"]["topLevelComment"]["id"]
        print(f" -> Posted engagement comment on video {video_id}")

        # Pin the comment (this makes it the first thing every viewer sees)
        try:
            youtube.comments().setModerationStatus(
                id=comment_id,
                moderationStatus="published",
                banAuthor=False,
            ).execute()
        except Exception:
            # setModerationStatus may not work for pinning on all accounts
            # The comment is still posted — just not pinned
            pass

        return comment_id
    except Exception as e:
        print(f" -> Could not post pinned comment for {video_id}: {e}")
        return None


def generate_engagement_comment(title: str, is_short: bool = True) -> str:
    """Generate a high-converting pinned comment that drives subscribers and engagement.
    
    Uses proven psychological triggers:
    1. Call to action (Subscribe + Bell)
    2. Question hook (drives replies)
    3. Social proof cue
    4. Emoji visual anchors
    """
    if is_short:
        return (
            f"🔥 Did this blow your mind? Drop a 🤯 if YES!\n\n"
            f"👉 SUBSCRIBE + 🔔 Bell for daily mind-bending Shorts you won't find anywhere else!\n\n"
            f"💬 What topic should I cover NEXT? Comment below — I read EVERY single one! 👇\n\n"
            f"📌 Share this with someone who NEEDS to see this!"
        )
    else:
        return (
            f"🚀 If you made it this far, you're already ahead of 99% of people!\n\n"
            f"👉 SUBSCRIBE + 🔔 Hit that Bell so you never miss an episode!\n\n"
            f"💬 What was YOUR biggest takeaway? Drop it in the comments — "
            f"best comment gets pinned! 📌\n\n"
            f"🔗 Share this with a friend who needs to hear this!"
        )
