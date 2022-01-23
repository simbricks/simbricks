/* -*- P4_16 -*- */

#include <core.p4>
#include <tna.p4>

/*************************************************************************
 ************* C O N S T A N T S    A N D   T Y P E S  *******************
**************************************************************************/
enum bit<16> ether_type_t {
    IPV4  = 0x0800,
    ARP   = 0x0806,
    TPID  = 0x8100,
    TPID2 = 0x9100,
    IPV6  = 0x86DD
}

const ReplicationId_t L2_MCAST_RID = 0xFFFF;

const int MAC_TABLE_SIZE        = 65536;
const int VLAN_PORT_TABLE_SIZE  = 1 << (7 + 12);

/* We can use up to 8 different digest types */
const bit<3> L2_LEARN_DIGEST = 1;

/*************************************************************************
 ***********************  H E A D E R S  *********************************
 *************************************************************************/

/*  Define all the headers the program will recognize             */
/*  The actual sets of headers processed by each gress can differ */

/* Standard ethernet header */
header ethernet_h {
    bit<48>   dst_addr;
    bit<48>   src_addr;
}

header vlan_tag_h {
    bit<16>  tpid;
    bit<3>   pcp;
    bit<1>   dei;
    bit<12>  vid;
}

header etherII_h {
    ether_type_t ether_type;
}

/*** Internal Headers ***/

typedef bit<4> header_type_t; /* These fields can be coombined into one      */
typedef bit<4> header_info_t; /* 8-bit field as well. Exercise for the brave */

const header_type_t HEADER_TYPE_BRIDGE         = 0xB;
const header_type_t HEADER_TYPE_MIRROR_INGRESS = 0xC;
const header_type_t HEADER_TYPE_MIRROR_EGRESS  = 0xD;
const header_type_t HEADER_TYPE_RESUBMIT       = 0xA;

/*
 * This is a common "preamble" header that must be present in all internal
 * headers. The only time you do not need it is when you know that you are
 * not going to have more than one internal header type ever
 */
#define INTERNAL_HEADER         \
    header_type_t header_type;  \
    header_info_t header_info


header inthdr_h {
    INTERNAL_HEADER;
}

/* Bridged metadata */
header bridge_h {
    INTERNAL_HEADER;

    bit<7>    pad0;
    PortId_t  ingress_port;

    bit<3>    pcp;
    bit<1>    dei;
    bit<12>   vid;
}

/*************************************************************************
 **************  I N G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

    /***********************  H E A D E R S  ************************/

struct my_ingress_headers_t {
    bridge_h     bridge;
    ethernet_h   ethernet;
    vlan_tag_h   vlan_tag;
    etherII_h    etherII;
}

    /******  G L O B A L   I N G R E S S   M E T A D A T A  *********/

struct port_metadata_t {
    bit<3>  port_pcp;
    bit<12> port_vid;
    bit<9>  l2_xid;
}

struct my_ingress_metadata_t {
    port_metadata_t port_properties;

    bit<3>   pcp;
    bit<1>   dei;
    bit<12>  vid;

    bit<9>   mac_move; /* Should have the same size as PortId_t */
    bit<1>   is_static;
    bit<1>   smac_hit;
    PortId_t ingress_port;
}

    /***********************  P A R S E R  **************************/
parser IngressParser(packet_in        pkt,
    /* User */
    out my_ingress_headers_t          hdr,
    out my_ingress_metadata_t         meta,
    /* Intrinsic */
    out ingress_intrinsic_metadata_t  ig_intr_md)
{
    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(ig_intr_md);
        meta.port_properties = port_metadata_unpack<port_metadata_t>(pkt);
        transition meta_init;
    }

    state meta_init {
        meta.pcp            = 0;
        meta.dei            = 0;
        meta.vid            = 0;
        meta.mac_move       = 0;
        meta.is_static      = 0;
        meta.smac_hit       = 0;
        meta.ingress_port   = ig_intr_md.ingress_port;
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(pkt.lookahead<bit<16>>()) {
            (bit<16>)ether_type_t.TPID &&& 0xEFFF: parse_vlan_tag;
            default: parse_etherII;
        }
    }

    state parse_vlan_tag {
        pkt.extract(hdr.vlan_tag);
        meta.pcp = hdr.vlan_tag.pcp;
        meta.dei = hdr.vlan_tag.dei;
        meta.vid = hdr.vlan_tag.vid;
        transition parse_etherII;
    }

    state parse_etherII {
        pkt.extract(hdr.etherII);
        transition accept;
    }
}

    /***************** M A T C H - A C T I O N  *********************/

control Ingress(
    /* User */
    inout my_ingress_headers_t                       hdr,
    inout my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_t               ig_intr_md,
    in    ingress_intrinsic_metadata_from_parser_t   ig_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t        ig_tm_md)
{
    action drop() {
        ig_dprsr_md.drop_ctl = 1;
    }

    action send(PortId_t port) {
        ig_tm_md.ucast_egress_port = port;
    }

    action smac_hit(PortId_t port, bit<1> is_static) {
        meta.mac_move  = ig_intr_md.ingress_port ^ port;
        meta.smac_hit  = 1;
        meta.is_static = is_static;
    }

    action smac_miss() { }

    action smac_drop() {
        drop(); exit;
    }

    @idletime_precision(3)
    table smac {
        key = {
            meta.vid              : exact;
            hdr.ethernet.src_addr : exact;
        }
        actions = {
            smac_hit; smac_miss; smac_drop;
        }
        size                 = MAC_TABLE_SIZE;
        const default_action = smac_miss();
        idle_timeout         = true;
    }

    action mac_learn_notify() {
        ig_dprsr_md.digest_type = L2_LEARN_DIGEST;
    }

    table smac_results {
        key = {
            meta.mac_move  : ternary;
            meta.is_static : ternary;
            meta.smac_hit  : ternary;
        }
        actions = {
            mac_learn_notify; NoAction; smac_drop;
        }
        const entries = {
            ( _, _, 0) : mac_learn_notify();
            ( 0, _, 1) : NoAction();
            ( _, 0, 1) : mac_learn_notify();
            ( _, 1, 1) : smac_drop();
        }
    }

    action dmac_unicast(PortId_t port) {
        send(port);
    }

    action dmac_miss() {
        ig_tm_md.mcast_grp_a = (MulticastGroupId_t)meta.vid;
        ig_tm_md.rid         = L2_MCAST_RID;
        /* Set the exclusion id here, since parser can't acces ig_tm_md */
        ig_tm_md.level2_exclusion_id = meta.port_properties.l2_xid;
    }

    action dmac_multicast(MulticastGroupId_t mcast_grp) {
        ig_tm_md.mcast_grp_a = mcast_grp;
        ig_tm_md.rid         = L2_MCAST_RID;
        /* Set the exclusion id here, since parser can't acces ig_tm_md */
        ig_tm_md.level2_exclusion_id = meta.port_properties.l2_xid;
    }

    action dmac_drop() {
        drop();
        exit;
    }

    table dmac {
        key = {
            meta.vid              : exact;
            hdr.ethernet.dst_addr : exact;
        }
        actions = {
            dmac_unicast; dmac_miss; dmac_multicast; dmac_drop;
        }
        size           = MAC_TABLE_SIZE;
        default_action = dmac_miss();
    }

    apply {
        /* Assign Port-based VLAN to untagged/priority-tagged packets */
        if (meta.vid == 0) {
            meta.vid = meta.port_properties.port_vid;
        }

        if (!hdr.vlan_tag.isValid()) {
            meta.pcp = meta.port_properties.port_pcp;
        }

        smac.apply();
        smac_results.apply();
        switch (dmac.apply().action_run) {
            dmac_unicast: { /* Unicast source pruning */
                if (ig_intr_md.ingress_port ==
                    ig_tm_md.ucast_egress_port) {
                    drop();
                }
            }
        }

        /* Bridge metadata to the egress pipeline */
        hdr.bridge.setValid();
        hdr.bridge.header_type  = HEADER_TYPE_BRIDGE;
        hdr.bridge.header_info  = 0;                           /* Ignore */
        hdr.bridge.ingress_port = ig_intr_md.ingress_port;
        hdr.bridge.pcp          = meta.pcp;
        hdr.bridge.dei          = meta.dei;
        hdr.bridge.vid          = meta.vid;
    }
}

    /*********************  D E P A R S E R  ************************/

/* This struct is needed for proper digest receive API generation */
struct l2_digest_t {
    bit<12> vid;
    bit<48> src_mac;
    bit<9>  ingress_port;
    bit<9>  mac_move;
    bit<1>  is_static;
    bit<1>  smac_hit;
}

control IngressDeparser(packet_out pkt,
    /* User */
    inout my_ingress_headers_t                       hdr,
    in    my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md)
{
    Digest <l2_digest_t>() l2_digest;

    apply {
        if (ig_dprsr_md.digest_type == L2_LEARN_DIGEST) {
            l2_digest.pack({
                    meta.vid,
                    hdr.ethernet.src_addr,
                    meta.ingress_port,
                    meta.mac_move,
                    meta.is_static,
                    meta.smac_hit });
        }

        pkt.emit(hdr);
    }
}


/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

    /***********************  H E A D E R S  ************************/

struct my_egress_headers_t {
    ethernet_h ethernet;
    vlan_tag_h vlan_tag;
    etherII_h  etherII;
}

    /********  G L O B A L   E G R E S S   M E T A D A T A  *********/

struct my_egress_metadata_t {
    bridge_h          bridge;

    PortId_t          ingress_port;
    bit<3>            pcp;
    bit<1>            dei;
    bit<12>           vid;
}

    /***********************  P A R S E R  **************************/

parser EgressParser(packet_in        pkt,
    /* User */
    out my_egress_headers_t          hdr,
    out my_egress_metadata_t         meta,
    /* Intrinsic */
    out egress_intrinsic_metadata_t  eg_intr_md)
{
    inthdr_h inthdr;

    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(eg_intr_md);
        inthdr = pkt.lookahead<inthdr_h>();
        transition select(inthdr.header_type, inthdr.header_info) {
            ( HEADER_TYPE_BRIDGE,         _ ) : parse_bridge;
            default : reject;
        }
    }

    state parse_bridge {
        pkt.extract(meta.bridge);
        meta.ingress_port = meta.bridge.ingress_port;
        meta.pcp = meta.bridge.pcp;
        meta.dei = meta.bridge.dei;
        meta.vid = meta.bridge.vid;
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(pkt.lookahead<bit<16>>()) {
            (bit<16>)ether_type_t.TPID &&& 0xEFFF: parse_vlan_tag;
            default: parse_etherII;
        }
    }

    state parse_vlan_tag {
        pkt.extract(hdr.vlan_tag);
        transition parse_etherII;
    }

    state parse_etherII {
        pkt.extract(hdr.etherII);
        transition accept;
    }
}

    /***************** M A T C H - A C T I O N  *********************/

control Egress(
    /* User */
    inout my_egress_headers_t                          hdr,
    inout my_egress_metadata_t                         meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_t                  eg_intr_md,
    in    egress_intrinsic_metadata_from_parser_t      eg_prsr_md,
    inout egress_intrinsic_metadata_for_deparser_t     eg_dprsr_md,
    inout egress_intrinsic_metadata_for_output_port_t  eg_oport_md)
{
    action drop() {
        eg_dprsr_md.drop_ctl = eg_dprsr_md.drop_ctl | 1;
    }

    action send_tagged() {
        hdr.vlan_tag.setValid();
        hdr.vlan_tag.tpid = (bit<16>)ether_type_t.TPID;
#ifdef P4C_1719_FIXED
        hdr.vlan_tag.pcp  = meta.pcp;
        hdr.vlan_tag.dei  = meta.dei;
#else
        hdr.vlan_tag.pcp  = 0;
        hdr.vlan_tag.dei  = 0;
#endif
        hdr.vlan_tag.vid  = meta.vid;
    }

    action send_untagged() {
        hdr.vlan_tag.setInvalid();
    }

    action not_a_member() {
        drop();
    }

    table egr_vlan_port {
        key = {
            meta.vid                    : exact;
#ifdef USE_MASK
            eg_intr_md.egress_port & 0x7F : exact @name("egress_port");
#else
            eg_intr_md.egress_port[6:0]   : exact @name("egress_port");
#endif
        }
        actions = {
            send_tagged;
            send_untagged;
            not_a_member;
        }
        default_action = not_a_member();
        size = VLAN_PORT_TABLE_SIZE;
    }

    apply {
#ifdef P4_SOURCE_PRUNING
        if (meta.ingress_port == eg_intr_md.egress_port) {
            drop();
        } else {
#endif
            egr_vlan_port.apply();
#ifdef P4_SOURCE_PRUNING
        }
#endif
    }
}

    /*********************  D E P A R S E R  ************************/

control EgressDeparser(packet_out pkt,
    /* User */
    inout my_egress_headers_t                       hdr,
    in    my_egress_metadata_t                      meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_for_deparser_t  eg_dprsr_md)
{
    apply {
        pkt.emit(hdr);
    }
}


/************ F I N A L   P A C K A G E ******************************/
Pipeline(
    IngressParser(),
    Ingress(),
    IngressDeparser(),
    EgressParser(),
    Egress(),
    EgressDeparser()
) pipe;

Switch(pipe) main;
