from bfrtcli import *
#from netaddr import *

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
        self.p4 = bfrt.l2_switch.pipe
        self.vlan       = {}
        self.all_ports  = [port.key[b'$DEV_PORT']
                           for port in bfrt.port.port.get(regex=1,
                                                          return_ents=True,
                                                          print_ents=False)]
        self.l2_age_ttl = default_ttl
        if (hasattr(self.p4.Egress, 'port_vlan_member') and
            hasattr(self.p4.Egress, 'port_vlan_tagged')):
            self.egr_vlan_port = False
        else:
            self.egr_vlan_port = True

    def setup(self):
        self.clear_all()
        self.__init__()

        # Preset port properties and the multicast pruning
        for dp in self.all_ports:
            l2_xid = self.mcport(*self.pipeport(dp))
            self.p4.IngressParser.PORT_METADATA.entry(ingress_port=dp,
                                   port_vid=0, port_pcp=0,
                                   l2_xid=l2_xid).push()

            bfrt.pre.prune.entry(MULTICAST_L2_XID=l2_xid, DEV_PORT=[dp]).push()

        # Ensure that egr_port_vlan (or its equivalent) is in asymmetric mode
        if self.egr_vlan_port:
            self.p4.Egress.egr_vlan_port.symmetric_mode_set(False)
        else:
            self.p4.Egress.port_vlan_member.symmetric_mode_set(False)
            self.p4.Egress.port_vlan_tagged.symmetric_mode_set(False)

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

        self.p4.Ingress.smac.idle_table_set_notify(enable=True,
                                                   callback=self.aging_cb,
                                                   interval = 10000,
                                                   min_ttl  = 10000,
                                                   max_ttl  = 60000)
        print("Done")

    @staticmethod
    def aging_cb(dev_id, pipe_id, direction, parser_id, entry):
        smac = bfrt.l2_switch.pipe.Ingress.smac
        dmac = bfrt.l2_switch.pipe.Ingress.dmac

        vid = entry.key[b'meta.vid']
        mac_addr = entry.key[b'hdr.ethernet.src_addr']

        print("Aging out: VID: {}, MAC: {}".format(vid, mac(mac_addr)))

        entry.remove() # from smac
        try:
            dmac.delete(vid=vid, dst_addr=mac_addr)
        except:
            print("WARNING: Could not find the matching DMAC entry")

    @staticmethod
    def learning_cb(dev_id, pipe_id, direction, parser_id, session, msg):
        smac = bfrt.l2_switch.pipe.Ingress.smac
        dmac = bfrt.l2_switch.pipe.Ingress.dmac

        for digest in msg:
            vid      = digest["vid"]
            port     = digest["ingress_port"]
            mac_move = digest["mac_move"]
            mac_addr  = digest["src_mac"]

            old_port = port ^ mac_move # Because mac_move = ingress_port ^ port

            print("VID: {},  MAC: {},  Port={}".format(
                vid, mac(mac_addr), port), end="")

            if mac_move != 0:
                print("(Move from port={})".format(old_port))
            else:
                print("(New)")

            # Since we do not have access to self, we have to use
            # the hardcoded value for the TTL :(
            smac.entry_with_smac_hit(vid=vid, src_addr=mac_addr,
                                     port=port,
                                     is_static=False,
                                     ENTRY_TTL=60000).push()
            dmac.entry_with_dmac_unicast(vid=vid, dst_addr=mac_addr,
                                         port=port).push()
        return 0

    def vlan_create(self, vid):
        if vid in self.vlan:
            raise KeyError("Vlan {} already exists".format(vid))
        if not 1 <= vid <= 4095:
            raise ValueError("Vlan ID {} is incorrect".format(vid))

        bfrt.pre.node.entry(MULTICAST_NODE_ID = vid,
                            MULTICAST_RID     = 0xFFFF, # See P4 code
                            MULTICAST_LAG_ID  = [ ],
                            DEV_PORT          = [ ]).push()
        bfrt.pre.mgid.entry(MGID = vid,
                            MULTICAST_NODE_ID           = [vid],
                            MULTICAST_NODE_L1_XID_VALID = [0],
                            MULTICAST_NODE_L1_XID       = [0]).push()
        self.vlan[vid] = {
            "ports": {}
        }


    def vlan_destroy(self, vid):
        if vid not in self.vlan:
            raise KeyError("Vlan {}  doesn't exist".format(vid))

        vlan_mgid = bfrt.pre.mgid.get(vid, print_ents=False)

        # Remove the multicast group
        bfrt.pre.mgid.delete(MGID=vid)

        # Remove the corresponding (single) node
        bfrt.pre.node.delete(MULTICAST_NODE_ID = vid)

        # Remove all entries from egr_vlan_port
        bfrt.batch_begin()
        try:
            if self.egr_vlan_port:
                for pipe in range(0, 3):
                    # pipe=None
                    for e in self.p4.Egress.egr_vlan_port.get(
                        pipe=pipe, regex=1, print_ents=False,
                        vid='0x[0]*{X}'.format(vid)):
                        e.remove()
            else:
                for pipe in range(0, 3):
                    for p in range(0, 72):
                        self.p4.Egress.port_vlan_member.mod(vid << 7 | p,
                                                            0, pipe=pipe)
                        self.p4.Egress.port_vlan_tagged.mod(vid << 7 | p,
                                                            0, pipe=pipe)
        except:
            pass
        finally:
            bfrt.batch_end()
        del(self.vlan[vid])

    def vlan_show(self, vlans=None):
        if vlans is None:
            vlans = self.vlan.keys()

        print(
"""
+------+------------------------------------------
| VLAN | Ports (Tagged or Untagged)
+------+------------------------------------------""")
        for vid in sorted(vlans):
            print ('| {:>4d} | '.format(vid), end='')

            for p in sorted(self.vlan[vid]["ports"].keys()):
                print(p, end='')
                if self.vlan[vid]["ports"][p]:
                    print("(T)", end='')
                else:
                    print("(U)", end='')
            print()

        print( "+------+------------------------------------------")

    def vlan_port_add(self, vid, dp, tagged=False):
        if vid not in self.vlan:
            raise KeyError("Vlan %d doesn't exist" % vid)
        # Update the multicast Node
        vlan_node = bfrt.pre.node.get(MULTICAST_NODE_ID=vid,
                                      return_ents=True, print_ents=False)
        vlan_node.data[b'$DEV_PORT'].append(dp)
        vlan_node.push()

        # Update egr_vlan_port table with the proper action
        # Unfortunately push(pipe=xxx) doesn't work (DRV-3667), so we'll
        # explicitly delete the entry and then add it to avoid any
        # issues
        (pipe, port) = self.pipeport(dp)
        #pipe=None
        try:
            if self.egr_vlan_port:
                self.p4.Egress.egr_vlan_port.delete(
                    vid=vid, egress_port=port, pipe=pipe)
        except:
            pass

        if self.egr_vlan_port:
            # Using the egr_port_vlan table
            if tagged:
                self.p4.Egress.egr_vlan_port.add_with_send_tagged(
                    vid=vid, egress_port=port, pipe=pipe)
            else:
                self.p4.Egress.egr_vlan_port.add_with_send_untagged(
                    vid=vid, egress_port=port, pipe=pipe)
        else:
            # Using register equivalents
            print('port_vlan_member.mod({}/{}, 1, {}) ... '.format(
                vid, port, pipe),
                  end='', flush=True)
            self.p4.Egress.port_vlan_member.mod(
                vid << 7 | port, 1, pipe=pipe)
            print('Done', flush=True)
            if tagged:
                self.p4.Egress.port_vlan_tagged.mod(
                    vid << 7 | port, 1, pipe=pipe)
            else:
                 self.p4.Egress.port_vlan_tagged.mod(
                    vid << 7 | port, 0, pipe=pipe)

        # Update internal state
        vlan_ports = self.vlan[vid]["ports"]
        vlan_ports[dp] = tagged

    def vlan_port_delete(self, vid, dp):
        if vid not in self.vlan:
            raise KeyError("Vlan %d doesn't exist" % vid)

        vlan_node = bfrt.pre.node_get(MULTICAST_NODE_ID=vid,
                                      return_ents=True, print_ents=False)
        try:
            vlan_node.data[b'$DEV_PORT'].remove(dp)
        except:
            pass
        vlan_node.push()

        try:
            (pipe, port) = self.pipeport(dp)
            #pipe=None
            if self.egr_vlan_port:
                self.p4.Egress.egr_vlan_port.delete(
                    vid=vid, egress_port=port, pipe=pipe)
            else:
                self.p4.Egress.port_vlan_member.mod(
                    vid << 7 | port, 0, pipe=pipe)
                self.p4.Egress.port_vlan_tagged.mod(
                    vid << 7 | port, 0, pipe=pipe)

        except:
            pass

        try:
            del(self.vlan[vid]['ports'][dp])
        except:
            pass

    def port_vlan_default_set(self, dp, vid):
        e = self.p4.IngressParser.PORT_METADATA.get(ingress_port=dp,
                                                    return_ents=True,
                                                    print_ents=False)
        e.data[b'port_vid'] = vid
        e.push()

    def port_vlan_default_get(self, dp):
        return self.p4.IngressParser.PORT_METADATA.get(
            ingress_port=dp,
            return_ents=True, print_ents=False).data[b'port_vid']

    def port_vlan_default_show(self, ports=None, show_all=False):
        if ports is None:
            ports = self.all_ports
        else:
            if not isinstance(ports, list):
                ports = [ports]
        for dp in sorted(ports):
            try:
                default_vid = self.port_vlan_default_get(dp)
                if default_vid != 0 or show_all:
                    print("Port %3d : Default VLAN is %4d" % (dp, default_vid))
            except:
                pass

    def l2_lookup(self, vid, mac_addr):
        dmac_entry = self.p4.Ingress.dmac.get(vid=vid, dst_addr=mac_addr,
                                         return_ents=True, print_ents=False)
        if dmac_entry == -1:
            dmac_entry = None

        smac_entry = self.p4.Ingress.smac.get(vid=vid, src_addr=mac_addr,
                                         return_ents=True, print_ents=False)
        if smac_entry == -1:
            smac_entry = None

        return (dmac_entry, smac_entry)

    def l2_add_smac_drop(self, vid, mac_addr):
        mac_addr = mac(mac_addr)
        self.p4.Ingress.smac.entry_with_smac_drop(
            vid=vid, src_addr=mac_addr).push()

    def l2_del(self, vid, mac_addr):
        mac_addr = mac(mac_addr)
        p4.Ingress.dmac.delete(vid=vid, dst_add=mac_addr)
        p4.Ingress.dmac.delete(vid=vid, src_add=mac_addr)

    def l2_print(self, dmac_entry, smac_entry):
        vid      = None
        mac_addr = None
        port     = "   "
        pending  = " "
        valid    = " "
        static   = " "
        dst_drop = " "
        src_drop = " "
        static   = " "
        ttl      = "      "
        dmac_eh_s= "          "
        smac_eh_s= "          "

        if dmac_entry is not None:
            valid    = "Y"
            vid      = dmac_entry.key[b'meta.vid']
            mac_addr = mac(dmac_entry.key[b'hdr.ethernet.dst_addr'])

            if dmac_entry.action.endswith("dmac_drop"):
                dst_drop = "Y"
            else:
                dst_drop = " "
                if dmac_entry.action.endswith("dmac_unicast"):
                    port = dmac_entry.data[b'port']

        if smac_entry is not None:
            valid       = "Y"
            ttl         = int(smac_entry.data[b'$ENTRY_TTL'])
            if ttl > 1000 or ttl == 0:
                ttl = "%6d" % (ttl/1000)
            else:
                ttl = " 0.%03d" % ttl

            if dmac_entry is None:
                vid      = smac_entry.key[b'meta.vid']
                mac_addr =  mac(smac_entry.key[b'hdr.ethernet.src_addr'])

            if smac_entry.action.endswith("smac_hit"):
                if (dmac_entry is None or
                    dmac_entry.action.endswith("dmac_miss")):
                    pending = "Y"
                    port = smac_entry.data[b'port']

                if smac_entry.data[b'is_static']:
                    static = "Y"
            elif smac_entry.action.endswith("smac_drop"):
                src_drop = "Y"

        if dmac_entry or smac_entry:
            print("| %4d | %s | %3d | %s %s %s | %s  %s | %s |" % (
                vid, mac_addr, port,
                valid, pending, static,
                src_drop, dst_drop,
                ttl))

    def l2_show(self, from_hw=True):
        dmac_entries={}
        try:
            for e in self.p4.Ingress.dmac.get(regex=1, from_hw=from_hw,
                                              print_ents=False,
                                              return_ents=True):
                dmac_entries[
                    (e.key[b'meta.vid'], e.key[b'hdr.ethernet.dst_addr'])] = e
        except:
            pass

        smac_entries = {}
        try:
            for e in self.p4.Ingress.smac.get(regex=1, from_hw=from_hw,
                                              print_ents=False,
                                              return_ents=True):
                smac_entries[
                    (e.key[b'meta.vid'], e.key[b'hdr.ethernet.src_addr'])] = e
        except:
            pass

        print (
"""
+------+-------------------+-----+-------+------+--------+
| VLAN |     MAC ADDR      |PORT | Flags | DROP | TTL(s) |
|      |                   |     | V P S | S  D |        |
+------+-------------------+-----+-------+------+--------+""")
        for (vid, mac_addr) in dmac_entries:
            dmac_entry = dmac_entries[(vid, mac_addr)]
            try:
                smac_entry = smac_entries[(vid, mac_addr)]
            except:
                smac_entry = None

            self.l2_print(dmac_entry, smac_entry)
            if smac_entry is not None:
                del(smac_entries[(vid, mac_addr)])

        for smac_entry in smac_entries.values():
            self.l2_print(None, smac_entry)

        print (
"""+------+-------------------+-----+-------+------+--------+""")


# Sample setup
sl2 = l2_switch(default_ttl=10000)
sl2.setup()
sl2.vlan_create(1)
sl2.vlan_port_add(1, 0)
sl2.vlan_port_add(1, 1)
sl2.vlan_port_add(1, 2)
sl2.vlan_port_add(1, 3)
sl2.port_vlan_default_set(0, 1)
sl2.port_vlan_default_set(1, 1)
sl2.port_vlan_default_set(2, 1)
sl2.port_vlan_default_set(3, 1)
sl2.l2_add_smac_drop(1, "00:00:00:00:00:00")
bfrt.complete_operations()

sl2.vlan_show()
sl2.port_vlan_default_show()
sl2.l2_show()
