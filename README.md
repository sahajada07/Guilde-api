# 🎮 Free Fire Guild Manager API v2.0

## Endpoints

### 1. /guild — Guild Basic Info
```
GET /guild?clan_id=3088932254&region=BD
```
**Response:**
```json
{
  "status": "success",
  "guild": {
    "id": 3088932254,
    "name": "GUILD_NAME",
    "level": 5,
    "score": 1200,
    "xp": 5000,
    "rank": 1,
    "region": "BD",
    "welcome_message": "Welcome!",
    "members_online": 3,
    "total_members": 20,
    "created_at": "2024-01-01 12:00:00",
    "last_active": "2025-03-10 18:00:00"
  }
}
```

---

### 2. /members — Guild সব Members Info
```
GET /members?clan_id=3088932254&region=BD
```
**Response:**
```json
{
  "status": "success",
  "guild": { ... },
  "members": [
    {
      "uid": 123456789,
      "nickname": "PlayerName",
      "level": 65,
      "is_online": true,
      "last_login": "2025-03-11 10:00:00",
      "br_rank": 8,
      "br_rank_points": 3200,
      "glory_points": 5400,
      "role": 1
    }
  ]
}
```
**Role values:** 1=Leader, 2=Co-leader, 3=Member

---

### 3. /player — Single Player Info
```
GET /player?uid=123456789&region=BD
```
**Response:**
```json
{
  "status": "success",
  "player": {
    "uid": 123456789,
    "nickname": "PlayerName",
    "level": 65,
    "exp": 12000,
    "likes": 500,
    "region": "BD",
    "is_online": false,
    "last_login": "2025-03-11 10:00:00",
    "guild_id": 3088932254,
    "guild_name": "GUILD_NAME"
  },
  "rank": {
    "br_rank": 8,
    "br_rank_points": 3200,
    "cs_rank": 6,
    "cs_rank_points": 1800,
    "glory_points": 5400
  }
}
```

---

### 4. /health — API Status
```
GET /health
```

---

## Regions
| Code | Region |
|------|--------|
| BD   | Bangladesh |
| IND  | India |
| BR   | Brazil |
| US/NA| North America |
| SG   | Singapore |

---

## নতুন Feature যোগ করার নিয়ম

`app.py`-এ নতুন route যোগ করো এইভাবে:

```python
@app.route('/new_feature', methods=['GET'])
def new_feature():
    # তোমার code এখানে
    return jsonify({"status": "success", "data": {}})
```

তারপর Vercel-এ redeploy করো — ব্যস! ✅
