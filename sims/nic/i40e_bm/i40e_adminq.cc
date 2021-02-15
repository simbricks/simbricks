/*
 * Copyright 2021 Max Planck Institute for Software Systems, and
 * National University of Singapore
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdlib.h>
#include <string.h>

#include <cassert>
#include <iostream>

#include "sims/nic/i40e_bm/i40e_base_wrapper.h"
#include "sims/nic/i40e_bm/i40e_bm.h"

using namespace i40e;

extern nicbm::Runner *runner;

queue_admin_tx::queue_admin_tx(i40e_bm &dev_, uint64_t &reg_base_,
                               uint32_t &reg_len_, uint32_t &reg_head_,
                               uint32_t &reg_tail_)
    : queue_base("atx", reg_head_, reg_tail_),
      dev(dev_),
      reg_base(reg_base_),
      reg_len(reg_len_) {
  desc_len = 32;
  ctxs_init();
}

queue_base::desc_ctx &queue_admin_tx::desc_ctx_create() {
  return *new admin_desc_ctx(*this, dev);
}

void queue_admin_tx::reg_updated() {
  base = reg_base;
  len = (reg_len & I40E_GL_ATQLEN_ATQLEN_MASK) >> I40E_GL_ATQLEN_ATQLEN_SHIFT;

  if (!enabled && (reg_len & I40E_GL_ATQLEN_ATQENABLE_MASK)) {
#ifdef DEBUG_ADMINQ
    log << " enable base=" << base << " len=" << len << logger::endl;
#endif
    enabled = true;
  } else if (enabled && !(reg_len & I40E_GL_ATQLEN_ATQENABLE_MASK)) {
#ifdef DEBUG_ADMINQ
    log << " disable" << logger::endl;
#endif
    enabled = false;
  }

  queue_base::reg_updated();
}

queue_admin_tx::admin_desc_ctx::admin_desc_ctx(queue_admin_tx &queue_,
                                               i40e_bm &dev_)
    : i40e::queue_base::desc_ctx(queue_), aq(queue_), dev(dev_) {
  d = reinterpret_cast<struct i40e_aq_desc *>(desc);
}

void queue_admin_tx::admin_desc_ctx::data_written(uint64_t addr, size_t len) {
  processed();
}

void queue_admin_tx::admin_desc_ctx::desc_compl_prepare(uint16_t retval,
                                                        uint16_t extra_flags) {
  d->flags &= ~0x1ff;
  d->flags |= I40E_AQ_FLAG_DD | I40E_AQ_FLAG_CMP | extra_flags;
  if (retval)
    d->flags |= I40E_AQ_FLAG_ERR;
  d->retval = retval;

#ifdef DEBUG_ADMINQ
  queue.log << " desc_compl_prepare index=" << index << " retval=" << retval
            << logger::endl;
#endif
}

void queue_admin_tx::admin_desc_ctx::desc_complete(uint16_t retval,
                                                   uint16_t extra_flags) {
  desc_compl_prepare(retval, extra_flags);
  processed();
}

void queue_admin_tx::admin_desc_ctx::desc_complete_indir(uint16_t retval,
                                                         const void *data,
                                                         size_t len,
                                                         uint16_t extra_flags,
                                                         bool ignore_datalen) {
  if (!ignore_datalen && len > d->datalen) {
    queue.log << "queue_admin_tx::desc_complete_indir: data too long (" << len
              << ") got buffer for (" << d->datalen << ")" << logger::endl;
    abort();
  }
  d->datalen = len;

  desc_compl_prepare(retval, extra_flags);

  uint64_t addr = d->params.external.addr_low |
                  (((uint64_t)d->params.external.addr_high) << 32);
  data_write(addr, len, data);
}

void queue_admin_tx::admin_desc_ctx::prepare() {
  if ((d->flags & I40E_AQ_FLAG_RD)) {
    uint64_t addr = d->params.external.addr_low |
                    (((uint64_t)d->params.external.addr_high) << 32);
#ifdef DEBUG_ADMINQ
    queue.log << " desc with buffer opc=" << d->opcode << " addr=" << addr
              << logger::endl;
#endif
    data_fetch(addr, d->datalen);
  } else {
    prepared();
  }
}

void queue_admin_tx::admin_desc_ctx::process() {
#ifdef DEBUG_ADMINQ
  queue.log << " descriptor " << index << " fetched" << logger::endl;
#endif

  if (d->opcode == i40e_aqc_opc_get_version) {
#ifdef DEBUG_ADMINQ
    queue.log << "  get version" << logger::endl;
#endif
    struct i40e_aqc_get_version *gv =
        reinterpret_cast<struct i40e_aqc_get_version *>(d->params.raw);
    gv->rom_ver = 0;
    gv->fw_build = 0;
    gv->fw_major = 0;
    gv->fw_minor = 0;
    gv->api_major = I40E_FW_API_VERSION_MAJOR;
    gv->api_minor = I40E_FW_API_VERSION_MINOR_X710;

    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_request_resource) {
#ifdef DEBUG_ADMINQ
    queue.log << "  request resource" << logger::endl;
#endif
    struct i40e_aqc_request_resource *rr =
        reinterpret_cast<struct i40e_aqc_request_resource *>(d->params.raw);
    rr->timeout = 180000;
#ifdef DEBUG_ADMINQ
    queue.log << "    res_id=" << rr->resource_id << logger::endl;
    queue.log << "    res_nu=" << rr->resource_number << logger::endl;
#endif
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_release_resource) {
#ifdef DEBUG_ADMINQ
    queue.log << "  release resource" << logger::endl;
#endif
#ifdef DEBUG_ADMINQ
    struct i40e_aqc_request_resource *rr =
        reinterpret_cast<struct i40e_aqc_request_resource *>(d->params.raw);
    queue.log << "    res_id=" << rr->resource_id << logger::endl;
    queue.log << "    res_nu=" << rr->resource_number << logger::endl;
#endif
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_clear_pxe_mode) {
#ifdef DEBUG_ADMINQ
    queue.log << "  clear PXE mode" << logger::endl;
#endif
    dev.regs.gllan_rctl_0 &= ~I40E_GLLAN_RCTL_0_PXE_MODE_MASK;
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_list_func_capabilities ||
             d->opcode == i40e_aqc_opc_list_dev_capabilities) {
#ifdef DEBUG_ADMINQ
    queue.log << "  get dev/fun caps" << logger::endl;
#endif
    struct i40e_aqc_list_capabilites *lc =
        reinterpret_cast<struct i40e_aqc_list_capabilites *>(d->params.raw);

    struct i40e_aqc_list_capabilities_element_resp caps[] = {
        {I40E_AQ_CAP_ID_RSS, 1, 0, 512, 6, 0, {}},
        {I40E_AQ_CAP_ID_RXQ, 1, 0, dev.NUM_QUEUES, 0, 0, {}},
        {I40E_AQ_CAP_ID_TXQ, 1, 0, dev.NUM_QUEUES, 0, 0, {}},
        {I40E_AQ_CAP_ID_MSIX, 1, 0, dev.NUM_PFINTS, 0, 0, {}},
        {I40E_AQ_CAP_ID_VSI, 1, 0, dev.NUM_VSIS, 0, 0, {}},
        {I40E_AQ_CAP_ID_DCB, 1, 0, 1, 1, 1, {}},
    };
    size_t num_caps = sizeof(caps) / sizeof(caps[0]);

    if (sizeof(caps) <= d->datalen) {
#ifdef DEBUG_ADMINQ
      queue.log << "    data fits" << logger::endl;
#endif
      // data fits within the buffer
      lc->count = num_caps;
      desc_complete_indir(0, caps, sizeof(caps));
    } else {
#ifdef DEBUG_ADMINQ
      queue.log << "    data doesn't fit" << logger::endl;
#endif
      // data does not fit
      d->datalen = sizeof(caps);
      desc_complete(I40E_AQ_RC_ENOMEM);
    }
  } else if (d->opcode == i40e_aqc_opc_lldp_stop) {
#ifdef DEBUG_ADMINQ
    queue.log << "  lldp stop" << logger::endl;
#endif
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_mac_address_read) {
#ifdef DEBUG_ADMINQ
    queue.log << "  read mac" << logger::endl;
#endif
    struct i40e_aqc_mac_address_read *ar =
        reinterpret_cast<struct i40e_aqc_mac_address_read *>(d->params.raw);

    struct i40e_aqc_mac_address_read_data ard;
    uint64_t mac = runner->GetMacAddr();
#ifdef DEBUG_ADMINQ
    queue.log << "    mac = " << mac << logger::endl;
#endif
    memcpy(ard.pf_lan_mac, &mac, 6);
    memcpy(ard.port_mac, &mac, 6);

    ar->command_flags = I40E_AQC_LAN_ADDR_VALID | I40E_AQC_PORT_ADDR_VALID;
    desc_complete_indir(0, &ard, sizeof(ard));
  } else if (d->opcode == i40e_aqc_opc_get_phy_abilities) {
#ifdef DEBUG_ADMINQ
    queue.log << "  get phy abilities" << logger::endl;
#endif
    struct i40e_aq_get_phy_abilities_resp par;
    memset(&par, 0, sizeof(par));

    par.phy_type = (1ULL << I40E_PHY_TYPE_40GBASE_CR4_CU);
    par.link_speed = I40E_LINK_SPEED_40GB;
    par.abilities = I40E_AQ_PHY_LINK_ENABLED | I40E_AQ_PHY_AN_ENABLED;
    par.eee_capability = 0;

    d->params.external.param0 = 0;
    d->params.external.param1 = 0;

    desc_complete_indir(0, &par, sizeof(par), 0, true);
  } else if (d->opcode == i40e_aqc_opc_get_link_status) {
#ifdef DEBUG_ADMINQ
    queue.log << "  link status" << logger::endl;
#endif
    struct i40e_aqc_get_link_status *gls =
        reinterpret_cast<struct i40e_aqc_get_link_status *>(d->params.raw);

    gls->command_flags &= I40E_AQ_LSE_IS_ENABLED;  // should actually return
                                                   // status of link status
                                                   // notification
    gls->phy_type = I40E_PHY_TYPE_40GBASE_CR4_CU;
    gls->link_speed = I40E_LINK_SPEED_40GB;
    gls->link_info = I40E_AQ_LINK_UP_FUNCTION | I40E_AQ_LINK_UP_PORT |
                     I40E_AQ_MEDIA_AVAILABLE | I40E_AQ_SIGNAL_DETECT;
    // might need qualified module
    gls->an_info = I40E_AQ_AN_COMPLETED | I40E_AQ_LP_AN_ABILITY;
    gls->ext_info = 0;
    gls->loopback = I40E_AQ_LINK_POWER_CLASS_4 << I40E_AQ_PWR_CLASS_SHIFT_LB;
    gls->max_frame_size = dev.MAX_MTU;
    gls->config = I40E_AQ_CONFIG_CRC_ENA;

    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_get_switch_config) {
#ifdef DEBUG_ADMINQ
    queue.log << "  get switch config" << logger::endl;
#endif
    struct i40e_aqc_switch_seid *sw =
        reinterpret_cast<struct i40e_aqc_switch_seid *>(d->params.raw);
    struct i40e_aqc_get_switch_config_header_resp hr;
    /* Not sure why dpdk doesn't like this?
    struct i40e_aqc_switch_config_element_resp els[] = {
        // EMC
        { I40E_AQ_SW_ELEM_TYPE_EMP, I40E_AQ_SW_ELEM_REV_1, 1, 513, 0, {},
            I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
        // MAC
        { I40E_AQ_SW_ELEM_TYPE_MAC, I40E_AQ_SW_ELEM_REV_1, 2, 0, 0, {},
            I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
        // PF
        { I40E_AQ_SW_ELEM_TYPE_PF, I40E_AQ_SW_ELEM_REV_1, 16, 512, 0, {},
            I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
        // VSI PF
        { I40E_AQ_SW_ELEM_TYPE_VSI, I40E_AQ_SW_ELEM_REV_1, 512, 2, 16, {},
            I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
        // VSI PF
        { I40E_AQ_SW_ELEM_TYPE_VSI, I40E_AQ_SW_ELEM_REV_1, 513, 2, 1, {},
            I40E_AQ_CONN_TYPE_REGULAR, 0, 0},
    };*/
    struct i40e_aqc_switch_config_element_resp els[] = {
        // VSI PF
        {I40E_AQ_SW_ELEM_TYPE_VSI,
         I40E_AQ_SW_ELEM_REV_1,
         512,
         2,
         16,
         {},
         I40E_AQ_CONN_TYPE_REGULAR,
         0,
         0},
    };

    // find start idx
    size_t cnt = sizeof(els) / sizeof(els[0]);
    size_t first = 0;
    for (first = 0; first < cnt && els[first].seid < sw->seid; first++) {
    }

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
#ifdef DEBUG_ADMINQ
    queue.log << "    report=" << report << " cnt=" << cnt
              << "  seid=" << sw->seid << logger::endl;
#endif

    // create temporary contiguous buffer
    size_t buflen = sizeof(hr) + sizeof(els[0]) * report;
    uint8_t buf[buflen];
    memcpy(buf, &hr, sizeof(hr));
    memcpy(buf + sizeof(hr), els + first, sizeof(els[0]) * report);

    desc_complete_indir(0, buf, buflen);
  } else if (d->opcode == i40e_aqc_opc_set_switch_config) {
#ifdef DEBUG_ADMINQ
    queue.log << "  set switch config" << logger::endl;
#endif
    /* TODO: lots of interesting things here like l2 filtering etc. that are
     * relevant.
    struct i40e_aqc_set_switch_config *sc =
        reinterpret_cast<struct i40e_aqc_set_switch_config *>(
                d->params.raw);
    */
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_get_vsi_parameters) {
#ifdef DEBUG_ADMINQ
    queue.log << "  get vsi parameters" << logger::endl;
#endif
    /*struct i40e_aqc_add_get_update_vsi *v =
        reinterpret_cast<struct i40e_aqc_add_get_update_vsi *>(
                d->params.raw);*/

    struct i40e_aqc_vsi_properties_data pd;
    memset(&pd, 0, sizeof(pd));
    pd.valid_sections |=
        I40E_AQ_VSI_PROP_SWITCH_VALID | I40E_AQ_VSI_PROP_QUEUE_MAP_VALID |
        I40E_AQ_VSI_PROP_QUEUE_OPT_VALID | I40E_AQ_VSI_PROP_SCHED_VALID;
    desc_complete_indir(0, &pd, sizeof(pd));
  } else if (d->opcode == i40e_aqc_opc_update_vsi_parameters) {
#ifdef DEBUG_ADMINQ
    queue.log << "  update vsi parameters" << logger::endl;
#endif
    /* TODO */
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_set_dcb_parameters) {
#ifdef DEBUG_ADMINQ
    queue.log << "  set dcb parameters" << logger::endl;
#endif
    /* TODO */
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_configure_vsi_bw_limit) {
#ifdef DEBUG_ADMINQ
    queue.log << "  configure vsi bw limit" << logger::endl;
#endif
    desc_complete(0);
  } else if (d->opcode == i40e_aqc_opc_query_vsi_bw_config) {
#ifdef DEBUG_ADMINQ
    queue.log << "  query vsi bw config" << logger::endl;
#endif
    struct i40e_aqc_query_vsi_bw_config_resp bwc;
    memset(&bwc, 0, sizeof(bwc));
    for (size_t i = 0; i < 8; i++) bwc.qs_handles[i] = 0xffff;
    desc_complete_indir(0, &bwc, sizeof(bwc));
  } else if (d->opcode == i40e_aqc_opc_query_vsi_ets_sla_config) {
#ifdef DEBUG_ADMINQ
    queue.log << "  query vsi ets sla config" << logger::endl;
#endif
    struct i40e_aqc_query_vsi_ets_sla_config_resp sla;
    memset(&sla, 0, sizeof(sla));
    for (size_t i = 0; i < 8; i++) sla.share_credits[i] = 127;
    desc_complete_indir(0, &sla, sizeof(sla));
  } else if (d->opcode == i40e_aqc_opc_remove_macvlan) {
#ifdef DEBUG_ADMINQ
    queue.log << "  remove macvlan" << logger::endl;
#endif
    struct i40e_aqc_macvlan *m =
        reinterpret_cast<struct i40e_aqc_macvlan *>(d->params.raw);
    struct i40e_aqc_remove_macvlan_element_data *rve =
        reinterpret_cast<struct i40e_aqc_remove_macvlan_element_data *>(data);
    for (uint16_t i = 0; i < m->num_addresses; i++)
      rve[i].error_code = I40E_AQC_REMOVE_MACVLAN_SUCCESS;

    desc_complete_indir(0, data, d->datalen);
  } else {
#ifdef DEBUG_ADMINQ
    queue.log << "  uknown opcode=" << d->opcode << logger::endl;
#endif
    // desc_complete(I40E_AQ_RC_ESRCH);
    desc_complete(0);
  }
}
