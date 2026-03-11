# player_pb2.py — Player & Member models (pure Python, no protobuf descriptor)

def _read_varint(data, pos):
    result = 0; shift = 0
    while pos < len(data):
        byte = data[pos]; pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80): break
        shift += 7
    return result, pos

def _write_varint(val):
    result = []
    while val > 0x7F:
        result.append((val & 0x7F) | 0x80)
        val >>= 7
    result.append(val & 0x7F)
    return bytes(result)

class PlayerRequest:
    def __init__(self): self.uid = 0
    def SerializeToString(self):
        return b'\x08' + _write_varint(self.uid)

class BasicInfo:
    def __init__(self):
        self.uid = 0; self.nickname = ""; self.level = 0; self.exp = 0
        self.likes = 0; self.region = ""; self.avatar_id = 0; self.banner_id = 0
        self.is_online = False; self.last_login = 0; self.account_created = 0
        self.guild_id = 0; self.guild_name = ""; self.guild_level = 0

class RankInfo:
    def __init__(self):
        self.br_rank = 0; self.br_rank_points = 0
        self.cs_rank = 0; self.cs_rank_points = 0; self.glory_points = 0

class PlayerResponse:
    def __init__(self):
        self.basic_info = BasicInfo(); self.rank_info = RankInfo()
    def ParseFromString(self, data):
        try:
            pos = 0
            while pos < len(data):
                tag_byte = data[pos]; pos += 1
                field_num = tag_byte >> 3; wire_type = tag_byte & 0x07
                if wire_type == 0:
                    val, pos = _read_varint(data, pos)
                    _apply_player_field(self.basic_info, self.rank_info, field_num, val)
                elif wire_type == 2:
                    length, pos = _read_varint(data, pos)
                    raw = data[pos:pos+length]; pos += length
                    if field_num in (1,2,3,4): _parse_nested_basic(self.basic_info, raw)
                    elif field_num in (5,6,7): _parse_nested_rank(self.rank_info, raw)
                    else:
                        s = raw.decode('utf-8', errors='replace')
                        _apply_player_string(self.basic_info, field_num, s)
                else: break
        except Exception: pass

class MemberInfo:
    def __init__(self):
        self.uid = 0; self.nickname = ""; self.level = 0
        self.is_online = False; self.last_login = 0
        self.br_rank = 0; self.br_rank_points = 0
        self.glory_points = 0; self.role = 3

class MemberListResponse:
    def __init__(self): self.members = []
    def ParseFromString(self, data):
        try:
            pos = 0
            while pos < len(data):
                tag_byte = data[pos]; pos += 1
                field_num = tag_byte >> 3; wire_type = tag_byte & 0x07
                if wire_type == 2:
                    length, pos = _read_varint(data, pos)
                    raw = data[pos:pos+length]; pos += length
                    if field_num == 1:
                        m = MemberInfo(); _parse_member(m, raw); self.members.append(m)
                elif wire_type == 0: _, pos = _read_varint(data, pos)
                else: break
        except Exception: pass

def _apply_player_field(basic, rank, field_num, val):
    if   field_num == 1:  basic.uid = val
    elif field_num == 7:  basic.level = val
    elif field_num == 8:  basic.exp = val
    elif field_num == 9:  basic.likes = val
    elif field_num == 16: basic.avatar_id = val
    elif field_num == 17: basic.banner_id = val
    elif field_num == 24: basic.is_online = bool(val)
    elif field_num == 13: basic.last_login = val
    elif field_num == 11: basic.account_created = val
    elif field_num == 26: rank.br_rank = val
    elif field_num == 27: rank.br_rank_points = val
    elif field_num == 28: rank.cs_rank = val
    elif field_num == 29: rank.cs_rank_points = val
    elif field_num == 30: rank.glory_points = val

def _apply_player_string(basic, field_num, s):
    if   field_num == 6:  basic.nickname = s
    elif field_num == 15: basic.region = s
    elif field_num == 57: basic.guild_name = s

def _parse_nested_basic(basic, data):
    pos = 0
    while pos < len(data):
        try:
            tag_byte = data[pos]; pos += 1
            field_num = tag_byte >> 3; wire_type = tag_byte & 0x07
            if wire_type == 0:
                val, pos = _read_varint(data, pos)
                if   field_num == 1:  basic.uid = val
                elif field_num == 7:  basic.level = val
                elif field_num == 8:  basic.exp = val
                elif field_num == 9:  basic.likes = val
                elif field_num == 24: basic.is_online = bool(val)
                elif field_num == 13: basic.last_login = val
                elif field_num == 11: basic.account_created = val
            elif wire_type == 2:
                length, pos = _read_varint(data, pos)
                raw = data[pos:pos+length]; pos += length
                s = raw.decode('utf-8', errors='replace')
                if   field_num == 6:  basic.nickname = s
                elif field_num == 15: basic.region = s
                elif field_num == 57: basic.guild_name = s
        except Exception: break

def _parse_nested_rank(rank, data):
    pos = 0
    while pos < len(data):
        try:
            tag_byte = data[pos]; pos += 1
            field_num = tag_byte >> 3; wire_type = tag_byte & 0x07
            if wire_type == 0:
                val, pos = _read_varint(data, pos)
                if   field_num == 1: rank.br_rank = val
                elif field_num == 2: rank.br_rank_points = val
                elif field_num == 3: rank.cs_rank = val
                elif field_num == 4: rank.cs_rank_points = val
                elif field_num == 5: rank.glory_points = val
            elif wire_type == 2:
                length, pos = _read_varint(data, pos)
                pos += length
        except Exception: break

def _parse_member(member, data):
    pos = 0
    while pos < len(data):
        try:
            tag_byte = data[pos]; pos += 1
            field_num = tag_byte >> 3; wire_type = tag_byte & 0x07
            if wire_type == 0:
                val, pos = _read_varint(data, pos)
                if   field_num == 1:  member.uid = val
                elif field_num == 7:  member.level = val
                elif field_num == 24: member.is_online = bool(val)
                elif field_num == 13: member.last_login = val
                elif field_num == 26: member.br_rank = val
                elif field_num == 27: member.br_rank_points = val
                elif field_num == 30: member.glory_points = val
                elif field_num == 50: member.role = val
            elif wire_type == 2:
                length, pos = _read_varint(data, pos)
                raw = data[pos:pos+length]; pos += length
                s = raw.decode('utf-8', errors='replace')
                if field_num == 6: member.nickname = s
        except Exception: break
