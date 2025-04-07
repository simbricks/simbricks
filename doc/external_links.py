"""Definition of external links that can be used in Sphinx as :<key>:`%s`"""

extlinks = {
    'simbricks-repo-plain': ('https://github.com/simbricks/simbricks%s', None),
    'simbricks-repo': ('https://github.com/simbricks/simbricks%s', 'README%s'),
    'simbricks-examples':
        ('https://github.com/simbricks/simbricks-examples%s', None),
    'gem5-fork': ('https://github.com/simbricks/gem5%s', None),
    'gem5-adapter': ('https://github.com/simbricks/gem5/blob/2c500a6a7527a1305e1a8e03f53ea11e90b71b73/src/simbricks/base.hh%s', 'gem5 Adapter%s'),
    'corundum-verilator-adapter': ('https://github.com/simbricks/simbricks/blob/57eeed65e91a467ce745b3880347f978c57e3beb/sims/nic/corundum/corundum_verilator.cc%s', 'Corundum Verilator Adapter%s'),
    'jped-decoder-adapter': ('https://github.com/simbricks/simbricks-examples/blob/main/hwaccel-jpeg-decoder/jpeg_decoder_verilator.cc%s', 'JPEG Decoder Verilator Adapter%s'),
    'ns3-adapter': ('https://github.com/simbricks/ns-3/blob/1ce6dca3b68da284eb0ce4a47f7790d0a0e745d8/src/simbricks/model/simbricks-base.cc%s', 'ns3 Adapter%s'),
    'verilator': ('https://www.veripool.org/verilator%s', 'Verilator%s'),
    'corundum': ('https://github.com/corundum/corundum%s', 'Corundum NIC%s'),
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
