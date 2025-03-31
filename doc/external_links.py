"""Definition of external links that can be used in Sphinx as :<key>:`%s`"""

extlinks = {
    'simbricks-repo-plain': ('https://github.com/simbricks/simbricks%s', None),
    'simbricks-repo': ('https://github.com/simbricks/simbricks%s', 'README%s'),
    'simbricks-examples':
        ('https://github.com/simbricks/simbricks-examples%s', None),
    'gem5-fork': ('https://github.com/simbricks/gem5%s', None),
    'slack': (
        'https://join.slack.com/t/simbricks/shared_invite/zt-16y96155y-xspnVcm18EUkbUHDcSVonA%s',
        None
    ),
    'mod-orchestration': (
        'https://github.com/simbricks/simbricks/blob/main/experiments/simbricks/orchestration/%s',
        'orchestration/%s'
    ),
    'lib-simbricks': (
        'https://github.com/simbricks/simbricks/blob/f260bf16b0bd110c3f1d48b851688f27c3f38a53/lib/simbricks/%s',
        'lib/simbricks/%s'
    ),
    'website': ('https://www.simbricks.io/%s', None),
}
