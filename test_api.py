import urllib.request, urllib.error
u='http://127.0.0.1:8000/api/proposals'
try:
    r=urllib.request.urlopen(u, timeout=5)
    print('OK', r.getcode())
    print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
except Exception as e:
    import traceback
    traceback.print_exc()
