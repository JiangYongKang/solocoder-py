from solocoder_py.credential import TrafficRouter, CredentialVersion

router = TrafficRouter()
router.register_rotation('test', 'old', 'new')
router.set_traffic_percentage('test', 100)

for i in range(5):
    router.route('test', f'req-{i}')
    router.record_metrics('test', CredentialVersion.NEW, is_error=True)

stats = router.get_stats('test')
print(f'After 5 new failures: consecutive_failures = {stats.new_consecutive_failures}')

router.route('test', 'req-old')
router.record_metrics('test', CredentialVersion.OLD, is_error=False)

stats = router.get_stats('test')
print(f'After 1 old success: consecutive_failures = {stats.new_consecutive_failures}')
print(f'Bug exists (cleared to 0): {stats.new_consecutive_failures == 0}')
print(f'Correct behavior (remains 5): {stats.new_consecutive_failures == 5}')
