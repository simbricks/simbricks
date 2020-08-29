#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"

using namespace i40e;

extern nicbm::Runner *runner;

queue_base::queue_base(uint32_t &reg_head_, uint32_t &reg_tail_)
    : base(0), len(0), fetch_head(0), reg_head(reg_head_), reg_tail(reg_tail_),
    enabled(false), desc_len(0)
{
}

void queue_base::trigger_fetch()
{
    if (fetch_head == reg_tail)
        return;


    dma_fetch *dma = new dma_fetch(*this, desc_len);
    dma->write = false;
    dma->dma_addr = base + fetch_head * desc_len;
    dma->index = fetch_head;

    std::cerr << "fetching " << (reg_tail - fetch_head) % len <<
        " descriptors from " << dma->dma_addr << std::endl;

    std::cerr << "dma = " << dma << std::endl;
    runner->issue_dma(*dma);
    fetch_head = (fetch_head + 1) % len;
}

void queue_base::reg_updated()
{
    if (!enabled)
        return;

    trigger_fetch();
}

void queue_base::desc_writeback(const void *desc, uint32_t idx)
{
    dma_wb *dma = new dma_wb(*this, desc_len);
    dma->write = true;
    dma->dma_addr = base + idx * desc_len;
    dma->index = idx;
    memcpy(dma->data, desc, desc_len);

    runner->issue_dma(*dma);
}

void queue_base::desc_writeback_indirect(const void *desc, uint32_t idx,
        uint64_t data_addr, const void *data, size_t data_len)
{
    // descriptor dma
    dma_wb *desc_dma = new dma_wb(*this, desc_len);
    desc_dma->write = true;
    desc_dma->dma_addr = base + idx * desc_len;
    desc_dma->index = idx;
    memcpy(desc_dma->data, desc, desc_len);
    // purposefully not issued yet, data dma will issue once ready

    // data dma
    dma_data_wb *data_dma = new dma_data_wb(*this, data_len, *desc_dma);
    data_dma->write = true;
    data_dma->dma_addr = data_addr;
    data_dma->index = idx;
    memcpy(data_dma->data, data, data_len);

    runner->issue_dma(*data_dma);
}

void queue_base::desc_written_back(uint32_t idx)
{
    std::cerr << "descriptor " << idx << " written back" << std::endl;
    reg_head = (idx + 1) % len;
}

queue_base::dma_fetch::dma_fetch(queue_base &queue_, size_t len_)
    : queue(queue_)
{
    data = new char[len_];
    len = len_;
}

queue_base::dma_fetch::~dma_fetch()
{
    delete[] ((char *) data);
}

void queue_base::dma_fetch::done()
{
    queue.desc_fetched(data, index);
    delete this;
}


queue_base::dma_wb::dma_wb(queue_base &queue_, size_t len_)
    : queue(queue_)
{
    data = new char[len_];
    len = len_;
}

queue_base::dma_wb::~dma_wb()
{
    delete[] ((char *) data);
}

void queue_base::dma_wb::done()
{
    queue.desc_written_back(index);
    queue.trigger_fetch();
    delete this;
}


queue_base::dma_data_wb::dma_data_wb(queue_base &queue_, size_t len_,
        dma_wb &desc_dma_)
    : queue(queue_), desc_dma(desc_dma_)
{
    data = new char[len_];
    len = len_;
}

queue_base::dma_data_wb::~dma_data_wb()
{
    delete[] ((char *) data);
}

void queue_base::dma_data_wb::done()
{
    // now we can issue descriptor dma
    runner->issue_dma(desc_dma);
    delete this;
}


/******************************************************************************/

queue_admin_tx::queue_admin_tx(i40e_bm &dev_, uint64_t &reg_base_,
        uint32_t &reg_len_, uint32_t &reg_head_, uint32_t &reg_tail_)
    : queue_base(reg_head_, reg_tail_), dev(dev_), reg_base(reg_base_),
    reg_len(reg_len_)
{
    desc_len = 32;
}

void queue_admin_tx::desc_compl_prepare(struct i40e_aq_desc *d, uint16_t retval,
        uint16_t extra_flags)
{
    d->flags &= ~0x1ff;
    d->flags |= I40E_AQ_FLAG_DD | I40E_AQ_FLAG_CMP | extra_flags;
    if (retval)
        d->flags |= I40E_AQ_FLAG_ERR;
    d->retval = retval;
}

void queue_admin_tx::desc_complete(struct i40e_aq_desc *d, uint32_t idx,
        uint16_t retval, uint16_t extra_flags)
{
    desc_compl_prepare(d, extra_flags, retval);
    desc_writeback(d, idx);
}

void queue_admin_tx::desc_complete_indir(struct i40e_aq_desc *d, uint32_t idx,
        uint16_t retval, const void *data, size_t len, uint16_t extra_flags)
{
    if (len > d->datalen) {
        std::cerr << "queue_admin_tx::desc_complete_indir: data too long ("
            << len << ") got buffer for (" << d->datalen << ")" << std::endl;
        abort();
    }
    d->datalen = len;

    desc_compl_prepare(d, extra_flags, retval);

    uint64_t addr = d->params.external.addr_low |
        (((uint64_t) d->params.external.addr_high) << 32);
    desc_writeback_indirect(d, idx, addr, data, len);

}

void queue_admin_tx::desc_fetched(void *desc, uint32_t idx)
{
    struct i40e_aq_desc *d = reinterpret_cast<struct i40e_aq_desc *>(desc);

    std::cerr << "descriptor " << idx << " fetched" << std::endl;

    if (d->opcode == i40e_aqc_opc_get_version) {
        std::cerr << "    get version" << std::endl;
        struct i40e_aqc_get_version *gv =
            reinterpret_cast<struct i40e_aqc_get_version *>(d->params.raw);
        gv->rom_ver = 0;
        gv->fw_build = 0;
        gv->fw_major = 0;
        gv->fw_minor = 0;
        gv->api_major = I40E_FW_API_VERSION_MAJOR;
        gv->api_minor = I40E_FW_API_VERSION_MINOR_X710;

        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_request_resource) {
        std::cerr << "    request resource" << std::endl;
        struct i40e_aqc_request_resource *rr =
            reinterpret_cast<struct i40e_aqc_request_resource *>(
                    d->params.raw);
        rr->timeout = 180000;
        std::cerr << "      res_id=" << rr->resource_id << std::endl;
        std::cerr << "      res_nu=" << rr->resource_number << std::endl;
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_release_resource) {
        std::cerr << "    release resource" << std::endl;
        struct i40e_aqc_request_resource *rr =
            reinterpret_cast<struct i40e_aqc_request_resource *>(
                    d->params.raw);
        std::cerr << "      res_id=" << rr->resource_id << std::endl;
        std::cerr << "      res_nu=" << rr->resource_number << std::endl;
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_clear_pxe_mode)  {
        std::cerr << "    clear PXE mode" << std::endl;
        dev.regs.gllan_rctl_0 &= ~I40E_GLLAN_RCTL_0_PXE_MODE_MASK;
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_list_func_capabilities ||
            d->opcode == i40e_aqc_opc_list_dev_capabilities)
    {
        std::cerr << "    get dev/fun caps" << std::endl;
        struct i40e_aqc_list_capabilites *lc =
            reinterpret_cast<struct i40e_aqc_list_capabilites *>(
                    d->params.raw);

        struct i40e_aqc_list_capabilities_element_resp caps[] = {
            { I40E_AQ_CAP_ID_RSS, 1, 0, 512, 6, 0, {} },
            { I40E_AQ_CAP_ID_RXQ, 1, 0, dev.NUM_QUEUES, 0, 0, {} },
            { I40E_AQ_CAP_ID_TXQ, 1, 0, dev.NUM_QUEUES, 0, 0, {} },
            { I40E_AQ_CAP_ID_MSIX, 1, 0, dev.NUM_PFINTS, 0, 0, {} },
        };
        size_t num_caps = sizeof(caps) / sizeof(caps[0]);

        if (sizeof(caps) <= d->datalen) {
            std::cerr << "      data fits" << std::endl;
            // data fits within the buffer
            lc->count = num_caps;
            desc_complete_indir(d, idx, 0, caps, sizeof(caps));
        } else {
            std::cerr << "      data doesn't fit" << std::endl;
            // data does not fit
            d->datalen = sizeof(caps);
            desc_complete(d, idx, I40E_AQ_RC_ENOMEM);
        }
    } else if (d->opcode == i40e_aqc_opc_lldp_stop) {
        std::cerr << "    lldp stop" << std::endl;
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_mac_address_read) {
        std::cerr << "    read mac" << std::endl;
        struct i40e_aqc_mac_address_read *ar =
            reinterpret_cast<struct i40e_aqc_mac_address_read *>(
                    d->params.raw);

        struct i40e_aqc_mac_address_read_data ard;
        uint64_t mac = runner->get_mac_addr();
        std::cerr << "      mac = " << mac << std::endl;
        memcpy(ard.pf_lan_mac, &mac, 6);
        memcpy(ard.port_mac, &mac, 6);

        ar->command_flags = I40E_AQC_LAN_ADDR_VALID | I40E_AQC_PORT_ADDR_VALID;
        desc_complete_indir(d, idx, 0, &ard, sizeof(ard));
    } else if (d->opcode == i40e_aqc_opc_get_link_status) {
        std::cerr << "    link status" << std::endl;
        struct i40e_aqc_get_link_status *gls =
            reinterpret_cast<struct i40e_aqc_get_link_status *>(
                    d->params.raw);

        gls->command_flags &= I40E_AQ_LSE_IS_ENABLED; // should actually return
                                                      // status of link status
                                                      // notification
        gls->phy_type = I40E_PHY_TYPE_40GBASE_CR4_CU;
        gls->link_speed = I40E_LINK_SPEED_40GB;
        gls->link_info = I40E_AQ_LINK_UP_FUNCTION | I40E_AQ_LINK_UP_PORT |
            I40E_AQ_MEDIA_AVAILABLE | I40E_AQ_SIGNAL_DETECT;
        gls->an_info = I40E_AQ_AN_COMPLETED | I40E_AQ_LP_AN_ABILITY; // might need qualified module
        gls->ext_info = 0;
        gls->loopback = I40E_AQ_LINK_POWER_CLASS_4 << I40E_AQ_PWR_CLASS_SHIFT_LB;
        gls->max_frame_size = dev.MAX_MTU;
        gls->config = I40E_AQ_CONFIG_CRC_ENA;

        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_get_switch_config) {
        std::cerr << "    get switch config" << std::endl;
        struct i40e_aqc_switch_seid *sw = reinterpret_cast<
            struct i40e_aqc_switch_seid *>(d->params.raw);
        struct i40e_aqc_get_switch_config_header_resp hr;
        struct i40e_aqc_switch_config_element_resp els[] = {
            // MAC
            { I40E_AQ_SW_ELEM_TYPE_MAC, I40E_AQ_SW_ELEM_REV_1, 1, 0, 0, {},
                I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
            // VSI
            { I40E_AQ_SW_ELEM_TYPE_VSI, I40E_AQ_SW_ELEM_REV_1, 2, 1, 3, {},
                I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
            // PF
            { I40E_AQ_SW_ELEM_TYPE_PF, I40E_AQ_SW_ELEM_REV_1, 3, 2, 0, {},
                I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
        };

        // find start idx
        size_t cnt = sizeof(els) / sizeof(els[0]);
        size_t first = 0;
        for (first = 0; first < cnt && els[first].seid < sw->seid; first++);

        // figure out how many fit in the buffer
        size_t max = (d->datalen - sizeof(hr)) / sizeof(els[0]);
        size_t report = cnt - first;
        if (report > max) {
            report = max;
            sw->seid = els[first + report].seid;
        } else {
            sw->seid = 0;
        }

        // prepare header
        memset(&hr, 0, sizeof(hr));
        hr.num_reported = report;
        hr.num_total = cnt;

        // create temporary contiguous buffer
        size_t buflen = sizeof(hr) + sizeof(els[0]) * report;
        uint8_t buf[buflen];
        memcpy(buf, &hr, sizeof(hr));
        memcpy(buf + sizeof(hr), els + first, sizeof(els[0]) * report);

        desc_complete_indir(d, idx, 0, buf, buflen);
    } else if (d->opcode == i40e_aqc_opc_set_switch_config) {
        std::cerr << "    set switch config" << std::endl;
        /* TODO: lots of interesting things here like l2 filtering etc. that are
         * relevant.
        struct i40e_aqc_set_switch_config *sc =
            reinterpret_cast<struct i40e_aqc_set_switch_config *>(
                    d->params.raw);
        */
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_get_vsi_parameters) {
        std::cerr << "    get vsi parameters" << std::endl;
        struct i40e_aqc_add_get_update_vsi *v =
            reinterpret_cast<struct i40e_aqc_add_get_update_vsi *>(
                    d->params.raw);

        struct i40e_aqc_vsi_properties_data pd;
        memset(&pd, 0, sizeof(pd));
        pd.valid_sections |= I40E_AQ_VSI_PROP_SWITCH_VALID |
            I40E_AQ_VSI_PROP_QUEUE_MAP_VALID |
            I40E_AQ_VSI_PROP_QUEUE_OPT_VALID |
            I40E_AQ_VSI_PROP_SCHED_VALID;
        desc_complete_indir(d, idx, 0, &pd, sizeof(pd));
    } else if (d->opcode == i40e_aqc_opc_update_vsi_parameters) {
        std::cerr << "    update vsi parameters" << std::endl;
        /* TODO */
        desc_complete(d, idx, 0);
    /*} else if (d->opcode == i40e_aqc_opc_remove_macvlan) { std::cerr << "    remove macvlan" << std::endl;*/
    } else if (d->opcode == i40e_aqc_opc_set_dcb_parameters) {
        std::cerr << "    set dcb parameters" << std::endl;
        /* TODO */
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_configure_vsi_bw_limit) {
        std::cerr << "    configure vsi bw limit" << std::endl;
        desc_complete(d, idx, 0);
    } else if (d->opcode == i40e_aqc_opc_query_vsi_bw_config) {
        struct i40e_aqc_query_vsi_bw_config_resp bwc;
        memset(&bwc, 0, sizeof(bwc));
        for (size_t i = 0; i < 8; i++)
            bwc.qs_handles[i] = 0xffff;
        desc_complete_indir(d, idx, 0, &bwc, sizeof(bwc));
    } else if (d->opcode == i40e_aqc_opc_query_vsi_ets_sla_config) {
        struct i40e_aqc_query_vsi_ets_sla_config_resp sla;
        memset(&sla, 0, sizeof(sla));
        for (size_t i = 0; i < 8; i++)
            sla.share_credits[i] = 127;
        desc_complete_indir(d, idx, 0, &sla, sizeof(sla));
    } else {
        std::cerr << "    uknown opcode=" << d->opcode << std::endl;
        desc_complete(d, idx, I40E_AQ_RC_ESRCH);
    }
}

void queue_admin_tx::reg_updated()
{
    base = reg_base;
    len = (reg_len & I40E_GL_ATQLEN_ATQLEN_MASK) >> I40E_GL_ATQLEN_ATQLEN_SHIFT;

    if (!enabled  && (reg_len & I40E_GL_ATQLEN_ATQENABLE_MASK)) {
        std::cerr << "enable atq base=" << base << " len=" << len << std::endl;
        enabled = true;
    } else if (enabled && !(reg_len & I40E_GL_ATQLEN_ATQENABLE_MASK)) {
        std::cerr << "disable atq" << std::endl;
        enabled = false;
    }

    queue_base::reg_updated();
}
