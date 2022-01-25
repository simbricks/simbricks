from bfrtcli import *

class l2_switch():
    #
    # Helper Functions to deal with ports
    #
    def devport(self, pipe, port):
        return ((pipe & 3) << 7) | (port & 0x7F)
    def pipeport(self,dp):
        return ((dp & 0x180) >> 7, (dp & 0x7F))
    def mcport(self, pipe, port):
        return pipe * 72 + port
    def devport_to_mcport(self, dp):
        return self.mcport(*self.pipeport(dp))


    # This is a useful bfrt_python function that should potentially allow one
    # to quickly clear all the logical tables (including the fixed ones) in
    #  their data plane program.
    #
    # This function  can clear all P4 tables and later other fixed objects
    # (once proper BfRt support is added). As of SDE-9.2.0 the support is mixed.
    # As a result the function contains some workarounds.
    def clear_all(self, verbose=True, batching=True, clear_ports=False):

        table_list = bfrt.info(return_info=True, print_info=False)

        # Remove port tables from the list
        port_types = ['PORT_CFG',      'PORT_FRONT_PANEL_IDX_INFO',
                      'PORT_HDL_INFO', 'PORT_STR_INFO']

        if not clear_ports:
            for table in list(table_list):
                if table['type'] in port_types:
                    table_list.remove(table)

                    # The order is important. We do want to clear from the top,
                    # i.e. delete objects that use other objects. For example,
                    # table entries use selector groups and selector groups
                    # use action profile members.
                    #
                    # Same is true for the fixed tables. However, the list of
                    # table types grows, so we will first clean the tables we
                    # know and then clear the rest
        for table_types in (['MATCH_DIRECT', 'MATCH_INDIRECT_SELECTOR'],
                            ['SELECTOR'],
                            ['ACTION_PROFILE'],
                            ['PRE_MGID'],
                            ['PRE_ECMP'],
                            ['PRE_NODE'],
                            []):         # This is catch-all
            for table in list(table_list):
                if table['type'] in table_types or len(table_types) == 0:
                    try:
                        if verbose:
                            print("Clearing table {:<40} ... ".
                                  format(table['full_name']),
                                  end='', flush=True)
                        table['node'].clear(batch=batching)
                        table_list.remove(table)
                        if verbose:
                            print('Done')
                        use_entry_list = False
                    except:
                        use_entry_list = True

                    # Some tables do not support clear(). Thus we'll try
                    # to get a list of entries and clear them one-by-one
                    if use_entry_list:
                        try:
                            if batching:
                                bfrt.batch_begin()

                            # This line can result in an exception,
                            # since # not all tables support get()
                            entry_list = table['node'].get(regex=True,
                                                           return_ents=True,
                                                           print_ents=False)

                            # Not every table supports delete() method.
                            # For those tables we'll try to push in an
                            # entry with everything being zeroed out
                            has_delete = hasattr(table['node'], 'delete')

                            if entry_list != -1:
                                if has_delete:
                                    for entry in entry_list:
                                        entry.remove()
                                else:
                                    clear_entry = table['node'].entry()
                                    for entry in entry_list:
                                        entry.data = clear_entry.data
                                        # We can still have an exception
                                        # here, since not all tables
                                        # support add()/mod()
                                        entry.push()
                                if verbose:
                                    print('Done')
                            else:
                                print('Empty')
                            table_list.remove(table)

                        except BfRtTableError as e:
                            print('Empty')
                            table_list.remove(table)

                        except Exception as e:
                            # We can have in a number of ways: no get(),
                            # no add() etc. Another reason is that the
                            # table is read-only.
                            if verbose:
                                print("Failed")
                        finally:
                            if batching:
                                bfrt.batch_end()
        bfrt.complete_operations()

    def __init__(self, default_ttl=60000):
        self.p4 = bfrt.nopaxos.pipe
        self.all_ports  = [port.key[b'$DEV_PORT']
                           for port in bfrt.port.port.get(regex=1,
                                                          return_ents=True,
                                                          print_ents=False)]
        self.l2_age_ttl = default_ttl

    def setup(self):
        self.clear_all()
        self.__init__()

        # Enable learning on SMAC
        print("Initializing learning on SMAC ... ", end='', flush=True)
        try:
            self.p4.IngressDeparser.l2_digest.callback_deregister()
        except:
            pass
        self.p4.IngressDeparser.l2_digest.callback_register(self.learning_cb)
        print("Done")

        # Enable aging on SMAC
        print("Inializing Aging on SMAC ... ", end='', flush=True)
        self.p4.Ingress.smac.idle_table_set_notify(enable=False,
                                                   callback=None)

        #self.p4.Ingress.smac.idle_table_set_notify(enable=True,
        #                                           callback=self.aging_cb,
        #                                           interval = 10000,
        #                                           min_ttl  = 10000,
        #                                           max_ttl  = 60000)
        print("Done")

    @staticmethod
    def aging_cb(dev_id, pipe_id, direction, parser_id, entry):
        smac = bfrt.nopaxos.pipe.Ingress.smac
        dmac = bfrt.nopaxos.pipe.Ingress.dmac

        mac_addr = entry.key[b'hdr.ethernet.src_addr']

        print("Aging out: MAC: {}".format(mac(mac_addr)))

        entry.remove() # from smac
        try:
            dmac.delete(dst_addr=mac_addr)
        except:
            print("WARNING: Could not find the matching DMAC entry")

    @staticmethod
    def learning_cb(dev_id, pipe_id, direction, parser_id, session, msg):
        smac = bfrt.nopaxos.pipe.Ingress.smac
        dmac = bfrt.nopaxos.pipe.Ingress.dmac

        for digest in msg:
            port     = digest["ingress_port"]
            mac_move = digest["mac_move"]
            mac_addr  = digest["src_mac"]

            old_port = port ^ mac_move # Because mac_move = ingress_port ^ port

            print("MAC: {},  Port={}".format(
                mac(mac_addr), port), end="")

            if mac_move != 0:
                print("(Move from port={})".format(old_port))
            else:
                print("(New)")

            # Since we do not have access to self, we have to use
            # the hardcoded value for the TTL :(
            smac.entry_with_smac_hit(src_addr=mac_addr,
                                     port=port,
                                     is_static=False,
                                     ENTRY_TTL=60000).push()
            dmac.entry_with_dmac_unicast(dst_addr=mac_addr,
                                         port=port).push()
        return 0

    def l2_add_smac_drop(self, vid, mac_addr):
        mac_addr = mac(mac_addr)
        self.p4.Ingress.smac.entry_with_smac_drop(
            src_addr=mac_addr).push()

def set_mcast(num_groups=1, num_sequencers=1):
    all_ports = [p for p in range(8)]
    mcast_ports = [0, 1, 2]
    # Broadcast
    bfrt.pre.node.entry(MULTICAST_NODE_ID=0, MULTICAST_RID=0,
        MULTICAST_LAG_ID=[], DEV_PORT=all_ports).push()
    bfrt.pre.mgid.entry(MGID=1, MULTICAST_NODE_ID=[0],
            MULTICAST_NODE_L1_XID_VALID=[False],
                MULTICAST_NODE_L1_XID=[0]).push()
    # Multicast
    bfrt.pre.node.entry(MULTICAST_NODE_ID=1, MULTICAST_RID=1,
        MULTICAST_LAG_ID=[], DEV_PORT=mcast_ports).push()
    bfrt.pre.mgid.entry(MGID=2, MULTICAST_NODE_ID=[1],
        MULTICAST_NODE_L1_XID_VALID=[False],
            MULTICAST_NODE_L1_XID=[0]).push()


### Setup L2 learning
sl2 = l2_switch(default_ttl=10000)
sl2.setup()
sl2.l2_add_smac_drop(1, "00:00:00:00:00:00")
bfrt.complete_operations()

p4 = bfrt.nopaxos.pipe
num_groups = 1
num_sequencers = 1

set_mcast(num_groups, num_sequencers)

### Register initialization
p4.Ingress.reg_cnt.mod(0, 0)
bfrt.complete_operations()

### Register print out
print("""******************* SETUP RESULTS *****************""")
print ("\n reg_cnt:")
p4.Ingress.reg_cnt.get(REGISTER_INDEX=0, from_hw=True)
