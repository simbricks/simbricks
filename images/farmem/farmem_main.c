#include<linux/module.h>
#include<linux/kernel.h>
#include <linux/memory_hotplug.h>
#include <linux/vmalloc.h>
#include <linux/pfn_t.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Antoine Kaufmann");
MODULE_DESCRIPTION("Manually exposes specified memory region in the specified "
    "numa node.");
MODULE_VERSION("0.1");

static unsigned long base_addr = 0;
static unsigned long size = 0;
static int nnid = 1;
static bool drain_node = false;

module_param(base_addr, ulong, 0);
module_param(size, ulong, 0);
module_param(nnid, int, 0);
module_param(drain_node, bool, 0);

/**
 * drains all available memory from the specified numa node by allocating (and
 * leaking) it
 */
static void do_drain_node(int nid)
{
  unsigned long eaten;
  struct page *p;

  printk(KERN_INFO "draining node %d\n", nid);
  if (nid == 0) {
    printk(KERN_ALERT "draining node 0 is probably a bad idea\n");
  }

  /* start with large chunks and move to smaller ones */
  eaten = 0;
  do {
    p = alloc_pages_node(nid,
      GFP_KERNEL | __GFP_NOWARN | __GFP_NORETRY | GFP_NOWAIT | __GFP_THISNODE,
      0);
    if (p)
      eaten += PAGE_SIZE;
  }
  /* Local memory is drained before farmem, therefore the following works. Tested on kernel 5.15.69.*/
  while (p && pfn_t_to_phys(page_to_pfn_t(p)) < base_addr);

  printk(KERN_INFO "drained %lu bytes\n", eaten);
}

static int __init farmem_mod_init(void)
{
  int rc;

  printk(KERN_ALERT "Loading farmem driver\n");
  if (!base_addr || !size) {
    panic("base address and length must be set");
  }

  if (!node_possible(nnid)) {
    panic("invalid numa node spcified");
  }

  if (drain_node)
    do_drain_node(nnid);

  rc = add_memory_driver_managed(nnid, base_addr, size,
      "System RAM (farmem)", MHP_NONE);
  if (rc) {
    printk(KERN_ALERT "adding memory failed: %d\n", rc);
  }
  node_set_online(nnid);

  /* Some local memory still remains usable, drain again to get it all. */
  if (drain_node)
    do_drain_node(nnid);

  return 0;
}

static void __exit farmem_mod_exit(void)
{
  printk(KERN_ALERT "Unloading farmem driver, this is broken\n");
}

module_init(farmem_mod_init);
module_exit(farmem_mod_exit);
