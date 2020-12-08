import itertools
import sys
import utils.parse_nopaxos

if len(sys.argv) != 2:
    print('Usage: nopaxos.py OUTDIR')
    sys.exit(1)

basedir = sys.argv[1] + '/'

types_of_seq = ['ehseq', 'swseq']
num_clients = [1, 2, 3, 4, 5, 6, 7, 8]



print('num_client ehseq-tput(req/sec) ehseq-lat(us) swseq-tput(req/sec) swseq-lat(us)\n')

for num_c in num_clients:
    line = [str(num_c)]
    for seq in types_of_seq:
        
        path_pat = '%snopaxos-gt-cb-%s-%d-1.json' % (basedir, seq, num_c)
        res = utils.parse_nopaxos.parse_nopaxos_run(num_c, seq, path_pat)
        #print(path_pat)

        if ((res['throughput'] is None) or (res['latency'] is None)):
            line.append('')
            line.append('')
            continue

        #print tput and avg. latency
        tput = res['throughput']
        lat = res['latency']

        line.append('%.2f' % (tput))
        line.append(f'{lat}')

    
    print(' '.join(line))
