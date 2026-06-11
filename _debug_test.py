import sys
sys.path.insert(0, 'src')
from solocoder_py.websocket import WebSocketSession, SimulatedWebSocketConnection, ReconnectConfig, ManualClock, SessionState

clock = ManualClock()
config = ReconnectConfig(initial_delay=1.0, max_attempts=0)
conn = SimulatedWebSocketConnection('test')
session = WebSocketSession(
    session_id='test',
    connection=conn,
    reconnect_config=config,
    clock=clock,
)
print('before tick, state:', session.state)
print('before tick, _closed:', session._closed)

try:
    session.tick()
except Exception as e:
    print('Error type:', type(e).__name__)
    print('Error:', e)
    import traceback
    traceback.print_exc()

print('after tick, state:', session.state)
print('after tick, _closed:', session._closed)
