import secrets,json
print(json.dumps({'WORK-PC':secrets.token_urlsafe(32),'HOME-PC':secrets.token_urlsafe(32)},indent=2))
