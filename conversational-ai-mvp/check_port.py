import socket
s = socket.socket()
s.settimeout(1)
r = s.connect_ex(('127.0.0.1', 8000))
print('Port 8000 open' if r == 0 else 'Port 8000 closed')
s.close()
