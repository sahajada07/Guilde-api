import httpx
import asyncio
import threading
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from datetime import datetime
import json

import data_pb2
import encode_id_clan_pb2
import player_pb2

# ============================================================
# CONFIG
# ============================================================
app = Flask(__name__)

FREEFIRE_VERSION = "OB52"

# AES Keys
API_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
API_IV  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# JWT Token store: { "BD": "token...", "IND": "token..." }
jwt_tokens = {}

# ============================================================
# REGION CONFIG
# ============================================================
REGION_URLS = {
    "IND": ("https://client.ind.freefiremobile.com", "client.ind.freefiremobile.com"),
    "BD":  ("https://client.bd.freefiremobile.com",  "client.bd.freefiremobile.com"),
    "BR":  ("https://client.br.freefiremobile.com",  "client.br.freefiremobile.com"),
    "SAC": ("https://client.br.freefiremobile.com",  "client.br.freefiremobile.com"),
    "US":  ("https://client.na.freefiremobile.com",  "client.na.freefiremobile.com"),
    "NA":  ("https://client.na.freefiremobile.com",  "client.na.freefiremobile.com"),
    "SG":  ("https://client.sg.freefiremobile.com",  "client.sg.freefiremobile.com"),
}

# ============================================================
# HELPERS
# ============================================================
def aes_encrypt(data_bytes):
    cipher = AES.new(API_KEY, AES.MODE_CBC, API_IV)
    return cipher.encrypt(pad(data_bytes, 16))

def aes_decrypt(data_bytes):
    cipher = AES.new(API_KEY, AES.MODE_CBC, API_IV)
    return unpad(cipher.decrypt(data_bytes), 16)

def ts(unix_time):
    if not unix_time:
        return None
    try:
        return datetime.fromtimestamp(unix_time).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return None

def get_headers(region, token):
    base_url, host = REGION_URLS.get(region.upper(), REGION_URLS["IND"])
    return {
        "Expect": "100-continue",
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": FREEFIRE_VERSION,
        "Content-Type": "application/octet-stream",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Host": host,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }, base_url

# ============================================================
# UID/PASSWORD LOADER
# ============================================================
def load_credentials():
    creds = {}
    try:
        with open("uidpass.txt", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Support both comma and colon separators
                sep = "," if "," in line else ":"
                parts = line.split(sep)
                if len(parts) != 3:
                    continue
                region, uid, password = parts
                region = region.upper().strip()
                if region not in creds:
                    creds[region] = (uid.strip(), password.strip())
    except FileNotFoundError:
        print("[-] uidpass.txt not found!")
    return creds

# ============================================================
# JWT TOKEN SYSTEM
# ============================================================
async def fetch_jwt_token(region):
    global jwt_tokens
    creds = load_credentials()
    region = region.upper()

    if region not in creds:
        print(f"[-] No credentials for region: {region}")
        return False

    uid, password = creds[region]
    url = f"https://fast-jwt-token-api.vercel.app/token?uid={uid}&password={password}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if "jwt_token" in data:
                    jwt_tokens[region] = data["jwt_token"]
                    print(f"[+] JWT updated for {region}")
                    return True
        print(f"[-] JWT failed for {region}: {resp.text[:100]}")
    except Exception as e:
        print(f"[-] JWT error for {region}: {e}")
    return False


async def token_updater_loop():
    regions = list(REGION_URLS.keys())
    while True:
        for region in regions:
            await fetch_jwt_token(region)
            await asyncio.sleep(3)
        print("[+] All tokens refreshed. Next refresh in 6 hours.")
        await asyncio.sleep(6 * 3600)


def start_token_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(token_updater_loop())


# ============================================================
# ROUTE: /guild  — Guild সব basic info
# ============================================================
@app.route('/guild', methods=['GET'])
def get_guild_info():
    clan_id = request.args.get('clan_id')
    region  = request.args.get('region', 'BD').upper()

    if not clan_id:
        return jsonify({"error": "clan_id is required", "example": "/guild?clan_id=3088932254&region=BD"}), 400

    token = jwt_tokens.get(region)
    if not token:
        return jsonify({"error": f"JWT token for {region} not ready. Wait a few seconds and retry."}), 503

    try:
        # Encode request
        my_data = encode_id_clan_pb2.MyData()
        my_data.field1 = int(clan_id)
        my_data.field2 = 1
        encrypted = aes_encrypt(my_data.SerializeToString())

        headers, base_url = get_headers(region, token)
        url = f"{base_url}/GetClanInfoByClanID"

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, content=encrypted)

        if resp.status_code != 200:
            return jsonify({"error": f"FF server returned HTTP {resp.status_code}"}), 500

        # Decode response
        parsed = data_pb2.response()
        parsed.ParseFromString(resp.content)

        return jsonify({
            "status": "success",
            "guild": {
                "id":              parsed.id,
                "name":            parsed.special_code,
                "level":           parsed.level,
                "score":           parsed.score,
                "xp":              parsed.xp,
                "rank":            parsed.rank,
                "region":          parsed.region,
                "welcome_message": parsed.welcome_message,
                "members_online":  parsed.guild_details.members_online,
                "total_members":   parsed.guild_details.total_members,
                "created_at":      ts(parsed.timestamp1),
                "updated_at":      ts(parsed.timestamp2),
                "last_active":     ts(parsed.last_active),
            }
        })

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


# ============================================================
# ROUTE: /player  — একজন Player-এর full info
# ============================================================
@app.route('/player', methods=['GET'])
def get_player_info():
    uid    = request.args.get('uid')
    region = request.args.get('region', 'BD').upper()

    if not uid:
        return jsonify({"error": "uid is required", "example": "/player?uid=123456789&region=BD"}), 400

    token = jwt_tokens.get(region)
    if not token:
        return jsonify({"error": f"JWT token for {region} not ready."}), 503

    try:
        # Encode player UID request
        req = player_pb2.PlayerRequest()
        req.uid = int(uid)
        encrypted = aes_encrypt(req.SerializeToString())

        headers, base_url = get_headers(region, token)
        url = f"{base_url}/GetPlayerPersonalShow"

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, content=encrypted)

        if resp.status_code != 200:
            return jsonify({"error": f"FF server returned HTTP {resp.status_code}"}), 500

        parsed = player_pb2.PlayerResponse()
        parsed.ParseFromString(resp.content)

        basic = parsed.basic_info
        rank  = parsed.rank_info

        return jsonify({
            "status": "success",
            "player": {
                "uid":            basic.uid,
                "nickname":       basic.nickname,
                "level":          basic.level,
                "exp":            basic.exp,
                "likes":          basic.likes,
                "region":         basic.region,
                "avatar_id":      basic.avatar_id,
                "banner_id":      basic.banner_id,
                "is_online":      basic.is_online,
                "last_login":     ts(basic.last_login),
                "account_created":ts(basic.account_created),
                "guild_id":       basic.guild_id,
                "guild_name":     basic.guild_name,
                "guild_level":    basic.guild_level,
            },
            "rank": {
                "br_rank":        rank.br_rank,
                "br_rank_points": rank.br_rank_points,
                "cs_rank":        rank.cs_rank,
                "cs_rank_points": rank.cs_rank_points,
                "glory_points":   rank.glory_points,
            }
        })

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


# ============================================================
# ROUTE: /members  — Guild-এর সব member-এর info একসাথে
# ============================================================
@app.route('/members', methods=['GET'])
def get_guild_members():
    clan_id = request.args.get('clan_id')
    region  = request.args.get('region', 'BD').upper()

    if not clan_id:
        return jsonify({"error": "clan_id is required", "example": "/members?clan_id=3088932254&region=BD"}), 400

    token = jwt_tokens.get(region)
    if not token:
        return jsonify({"error": f"JWT token for {region} not ready."}), 503

    try:
        # Step 1: Guild info আনো (member UID list পাওয়ার জন্য)
        my_data = encode_id_clan_pb2.MyData()
        my_data.field1 = int(clan_id)
        my_data.field2 = 1
        encrypted = aes_encrypt(my_data.SerializeToString())

        headers, base_url = get_headers(region, token)

        with httpx.Client(timeout=30) as client:
            guild_resp = client.post(
                f"{base_url}/GetClanInfoByClanID",
                headers=headers,
                content=encrypted
            )

        if guild_resp.status_code != 200:
            return jsonify({"error": f"FF server error: HTTP {guild_resp.status_code}"}), 500

        guild_parsed = data_pb2.response()
        guild_parsed.ParseFromString(guild_resp.content)

        # Step 2: Member list আনো
        member_req = encode_id_clan_pb2.MyData()
        member_req.field1 = int(clan_id)
        member_req.field2 = 2
        encrypted2 = aes_encrypt(member_req.SerializeToString())

        with httpx.Client(timeout=30) as client:
            members_resp = client.post(
                f"{base_url}/GetClanMemberList",
                headers=headers,
                content=encrypted2
            )

        members_data = []

        if members_resp.status_code == 200:
            try:
                member_list = player_pb2.MemberListResponse()
                member_list.ParseFromString(members_resp.content)

                for m in member_list.members:
                    members_data.append({
                        "uid":            m.uid,
                        "nickname":       m.nickname,
                        "level":          m.level,
                        "is_online":      m.is_online,
                        "last_login":     ts(m.last_login),
                        "br_rank":        m.br_rank,
                        "br_rank_points": m.br_rank_points,
                        "glory_points":   m.glory_points,
                        "role":           m.role,  # 1=Leader, 2=Co-leader, 3=Member
                    })
            except Exception:
                members_data = []

        return jsonify({
            "status": "success",
            "guild": {
                "id":             guild_parsed.id,
                "name":           guild_parsed.special_code,
                "level":          guild_parsed.level,
                "score":          guild_parsed.score,
                "members_online": guild_parsed.guild_details.members_online,
                "total_members":  guild_parsed.guild_details.total_members,
            },
            "members": members_data,
            "note": "members list may be empty if GetClanMemberList endpoint is unavailable"
        })

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


# ============================================================
# ROUTE: /health  — API status check
# ============================================================
@app.route('/health', methods=['GET'])
def health():
    token_status = {}
    for region in REGION_URLS:
        token_status[region] = "✅ ready" if jwt_tokens.get(region) else "⏳ not ready"

    return jsonify({
        "status":    "running",
        "version":   "2.0",
        "tokens":    token_status,
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "/guild":   "GET ?clan_id=&region=  → Guild info",
            "/members": "GET ?clan_id=&region=  → All members info",
            "/player":  "GET ?uid=&region=      → Single player info",
            "/health":  "GET                    → API status",
        }
    })


# ============================================================
# STARTUP
# ============================================================
if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Guild API v2.0 starting on port {port}...")

    # Token updater background thread
    t = threading.Thread(target=start_token_loop, daemon=True)
    t.start()

    app.run(host='0.0.0.0', port=port, debug=False)
