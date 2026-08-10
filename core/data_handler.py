import pandas as pd
import re
import os
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

def now_kst():
    """Cloud hosts (e.g. Streamlit Community Cloud) run in UTC by default,
    so timestamps must be pinned to Asia/Seoul explicitly rather than
    relying on datetime.now()'s naive local time."""
    return datetime.now(KST)

def mask_name(name):
    if not isinstance(name, str):
        return ""
    name_str = str(name).strip()
    if len(name_str) <= 4:
        return name_str + "***"
    return name_str[:4] + "*" * (len(name_str) - 4)

def mask_address(address):
    if pd.isna(address) or not str(address).strip():
        return ""
    address = str(address).strip()
    # Mask after Dong/Eup/Myeon/Ri/Ga
    match = re.search(r'([가-힣0-9]+(?:동|읍|면|리|가))(?:\s|$)', address)
    if match:
        end_idx = match.end(1)
        prefix = address[:end_idx]
        suffix = address[end_idx:]
        masked_suffix = "".join(['*' if not c.isspace() else c for c in suffix])
        return prefix + masked_suffix
    # Fallback masking
    parts = address.split(' ')
    if len(parts) <= 3:
        return address
    return " ".join(parts[:3]) + " *****"

def load_data(file_path_or_buffer):
    try:
        if isinstance(file_path_or_buffer, str) and file_path_or_buffer.endswith('.csv'):
            df = pd.read_csv(file_path_or_buffer, encoding='utf-8-sig')
        elif hasattr(file_path_or_buffer, 'name') and file_path_or_buffer.name.endswith('.csv'):
            df = pd.read_csv(file_path_or_buffer, encoding='utf-8-sig')
        else:
            df = pd.read_excel(file_path_or_buffer)
        
        # Find essential columns dynamically
        cols = df.columns.tolist()
        
        # Define mappings for common column names
        col_mappings = {
            'target_type': next((c for c in cols if '활동대상' in c or '담당채널' in c), None),
            'branch': next((c for c in cols if '지사' in c), None),
            'zone': next((c for c in cols if '구역' in c or '담당자' in c), None),
            'name': next((c for c in cols if '상호' in c), None),
            'address': next((c for c in cols if '설치주소' in c or '주소' in c), None),
            'status': next((c for c in cols if '상태' in c), None),
            'processor': next((c for c in cols if '처리자' in c), None),
            'coord': next((c for c in cols if '위치좌표' in c or '위경도' in c), None),
            'lat': next((c for c in cols if '위도' in c and '위치좌표' not in c), None),
            'lng': next((c for c in cols if '경도' in c and '위치좌표' not in c), None),
            'contract_no': next((c for c in cols if '계약번호' in c), None),
            'service_no': next((c for c in cols if '서비스번호' in c), None),
            'activity_status': next((c for c in cols if '활동유무' in c), None),
            'activity_detail': next((c for c in cols if '세부 활동내역' in c or '세부활동내역' in c), None),
            'modifier': next((c for c in cols if '최종수정자' in c), None),
            'modified_at': next((c for c in cols if '최종수정일시' in c), None),
        }
        
        processed_data = []
        for i, row in df.iterrows():
            lat, lng = None, None
            
            # Extract from combined coord column if present
            if col_mappings['coord'] and pd.notna(row[col_mappings['coord']]):
                coord_str = str(row[col_mappings['coord']]).strip()
                if ',' in coord_str:
                    try:
                        parts = coord_str.split(',')
                        lat = float(parts[0].strip())
                        lng = float(parts[1].strip())
                    except:
                        pass
            
            # Fallback to separate lat/lng columns
            if lat is None and col_mappings['lat'] and pd.notna(row[col_mappings['lat']]):
                lat = row[col_mappings['lat']]
            if lng is None and col_mappings['lng'] and pd.notna(row[col_mappings['lng']]):
                lng = row[col_mappings['lng']]
            
            # Require lat/lng for mapping
            if not lat or not lng:
                continue
                
            def safe_format(val):
                if pd.isna(val) or str(val).strip() == '':
                    return '-'
                val_str = str(val).strip().replace(',', '')
                if val_str.endswith('.0'):
                    return val_str[:-2]
                return val_str

            item = {
                'target_type': str(row[col_mappings['target_type']]).strip() if col_mappings['target_type'] and pd.notna(row[col_mappings['target_type']]) else '기타',
                'branch': str(row[col_mappings['branch']]).strip() if col_mappings['branch'] and pd.notna(row[col_mappings['branch']]) else '미지정',
                'zone': str(row[col_mappings['zone']]).strip() if col_mappings['zone'] and pd.notna(row[col_mappings['zone']]) else '미지정',
                'name': mask_name(row[col_mappings['name']]) if col_mappings['name'] else '',
                'address': mask_address(row[col_mappings['address']]) if col_mappings['address'] else '',
                'status': str(row[col_mappings['status']]).strip() if col_mappings['status'] and pd.notna(row[col_mappings['status']]) else '미접수',
                'processor': str(row[col_mappings['processor']]).strip() if col_mappings['processor'] and pd.notna(row[col_mappings['processor']]) else '-',
                'lat': float(lat),
                'lng': float(lng),
                'contract_no': safe_format(row[col_mappings['contract_no']]) if col_mappings['contract_no'] else '-',
                'service_no': safe_format(row[col_mappings['service_no']]) if col_mappings['service_no'] else '-',
                'activity_status': str(row[col_mappings['activity_status']]).strip() if col_mappings['activity_status'] and pd.notna(row[col_mappings['activity_status']]) else '미접수',
                'activity_detail': str(row[col_mappings['activity_detail']]).strip() if col_mappings['activity_detail'] and pd.notna(row[col_mappings['activity_detail']]) else '-',
                'modifier': str(row[col_mappings['modifier']]).strip() if col_mappings['modifier'] and pd.notna(row[col_mappings['modifier']]) else '',
                'modified_at': str(row[col_mappings['modified_at']]).strip() if col_mappings['modified_at'] and pd.notna(row[col_mappings['modified_at']]) else '',
                '_row_id': i,
            }
            # If target type is SE or SG and status is 방문상담, change it to 방문활동(표지판교체)
            if item['target_type'] in ['SE', 'SG'] and item['status'] == '방문상담':
                item['status'] = '방문활동(표지판교체)'

            # activity_status now mirrors status directly so custom statuses
            # (e.g. 활동중, 재계약거부) registered via update_activity() are reflected as-is
            item['activity_status'] = item['status']
            processed_data.append(item)
            
        return pd.DataFrame(processed_data)

    except Exception as e:
        return str(e)


def update_activity(file_path, row_id, new_status, detail, modifier):
    """Write a field activity update back into the shared db.csv so every
    session picks it up on its next reload (real-time-ish sharing)."""
    try:
        raw = pd.read_csv(file_path, encoding='utf-8-sig')
        if row_id not in raw.index:
            return False

        cols = raw.columns.tolist()
        status_col = next((c for c in cols if '상태' in c), None)
        activity_col = next((c for c in cols if '활동유무' in c), None)
        detail_col = next((c for c in cols if '세부 활동내역' in c or '세부활동내역' in c), None)

        # A column that's entirely blank (e.g. a fresh data export with no
        # activity yet) gets read in as float64 (all-NaN), which raises a
        # TypeError the moment a status string is written into it. Force
        # these columns to plain object dtype first so the write always works.
        for col in (status_col, activity_col, detail_col):
            if col and raw[col].dtype != object:
                raw[col] = raw[col].astype(object)

        if status_col:
            raw.loc[row_id, status_col] = new_status
        if activity_col:
            raw.loc[row_id, activity_col] = new_status
        if detail_col and detail:
            raw.loc[row_id, detail_col] = detail

        if '최종수정자' not in raw.columns:
            raw['최종수정자'] = ''
        if '최종수정일시' not in raw.columns:
            raw['최종수정일시'] = ''
        raw.loc[row_id, '최종수정자'] = modifier
        raw.loc[row_id, '최종수정일시'] = now_kst().strftime('%Y-%m-%d %H:%M:%S')

        raw.to_csv(file_path, index=False, encoding='utf-8-sig')
        return True
    except Exception:
        return False


def log_login(log_path, login_type, branch='-', target_type='-', zone='-'):
    """Append one row to the shared login history log (created on first use)."""
    try:
        entry = pd.DataFrame([{
            '로그인시각': now_kst().strftime('%Y-%m-%d %H:%M:%S'),
            '유형': login_type,
            '지사': branch,
            '활동대상구분': target_type,
            '구역': zone,
        }])
        if os.path.exists(log_path):
            existing = pd.read_csv(log_path, encoding='utf-8-sig')
            entry = pd.concat([existing, entry], ignore_index=True)
        entry.to_csv(log_path, index=False, encoding='utf-8-sig')
        return True
    except Exception:
        return False


def backup_to_github(file_path, repo_path, token, repo, commit_message):
    """Push a local file (login_log.csv, db.csv, ...) to GitHub as a backup.

    Streamlit Cloud's local disk resets on every redeploy/reboot/sleep, so
    this is what actually makes the data durable. Credentials are passed in
    (read from st.secrets by the caller) rather than imported here, so this
    module stays free of any Streamlit dependency. No-ops safely if token
    or repo is missing, so the app keeps working before secrets are set up.

    Returns (success, message) - message carries the actual failure reason
    (HTTP status + GitHub's error body, or the exception) instead of
    swallowing it, since "백업 실패" with no detail is undiagnosable.
    """
    if not token or not repo:
        return False, "GITHUB_TOKEN 또는 GITHUB_REPO가 설정되지 않았습니다."
    try:
        import requests
        import base64

        if not os.path.exists(file_path):
            return False, f"백업할 로컬 파일이 없습니다: {file_path}"

        with open(file_path, 'rb') as f:
            content_b64 = base64.b64encode(f.read()).decode('utf-8')

        api_url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

        get_resp = requests.get(api_url, headers=headers, timeout=10)
        sha = get_resp.json().get('sha') if get_resp.status_code == 200 else None
        if get_resp.status_code not in (200, 404):
            return False, f"GET 실패 (HTTP {get_resp.status_code}): {get_resp.text[:300]}"

        payload = {"message": commit_message, "content": content_b64}
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(api_url, headers=headers, json=payload, timeout=10)
        if put_resp.status_code in (200, 201):
            return True, "OK"
        return False, f"PUT 실패 (HTTP {put_resp.status_code}): {put_resp.text[:300]}"
    except Exception as e:
        return False, f"예외 발생: {e}"
