"""Definition of external links that can be used in Sphinx as :<key>:`%s`"""

extlinks = {
    'simbricks-repo-plain': ('https://github.com/simbricks/simbricks%s', None),
    'simbricks-repo': ('https://github.com/simbricks/simbricks%s', 'README%s'),
    'simbricks-examples':
        ('https://github.com/simbricks/simbricks-examples%s', None),
    'simbricks-paper': ('https://arxiv.org/abs/2012.14219%s', 'paper%s'),
    'gem5-fork': ('https://github.com/simbricks/gem5%s', None),
    'gem5-adapter': ('https://github.com/simbricks/gem5/blob/2c500a6a7527a1305e1a8e03f53ea11e90b71b73/src/simbricks/base.hh%s', 'gem5 Adapter%s'),
    'corundum-verilator-adapter': ('https://github.com/simbricks/simbricks/blob/57eeed65e91a467ce745b3880347f978c57e3beb/sims/nic/corundum/corundum_verilator.cc%s', 'Corundum Verilator Adapter%s'),
    'jped-decoder-adapter': ('https://github.com/simbricks/simbricks-examples/blob/main/hwaccel-jpeg-decoder/jpeg_decoder_verilator.cc%s', 'JPEG Decoder Verilator Adapter%s'),
    'ns3-adapter': ('https://github.com/simbricks/ns-3/blob/1ce6dca3b68da284eb0ce4a47f7790d0a0e745d8/src/simbricks/model/simbricks-base.cc%s', 'ns3 Adapter%s'),
    'verilator': ('https://www.veripool.org/verilator%s', 'Verilator%s'),
    'corundum': ('https://github.com/corundum/corundum%s', 'Corundum NIC%s'),
    'qemu': ('https://www.qemu.org%s', 'QEMU%s'),
    'gem5': ('https://www.gem5.org%s', 'gem5%s'),
    'simics': ('https://www.intel.com/content/www/us/en/developer/articles/tool/simics-simulator.html%s', 'Simics%s'),
    'ns3': ('https://www.nsnam.org%s', 'ns-3%s'),
    'omnet': ('https://inet.omnetpp.org%s', 'OMNeT++ INET%s'),
    'tofino': ('https://www.intel.com/content/www/us/en/products/network-io/programmable-ethernet-switch/p4-suite/p4-studio.html%s', 'Intel Tofino SDK Simulator%s'),
    'femu': ('https://github.com/ucare-uchicago/FEMU%s', 'FEMU%s'),
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
    'docker-hub': ('https://hub.docker.com/u/simbricks%s', 'Docker Hub%s'),
    'dev-container': ('https://code.visualstudio.com/docs/remote/containers%s', 'Visual Studio Code Development Container%s'),
    'dev-container-ext': ('https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers%s', 'VS Code Dev Containers extension%s'),
}
