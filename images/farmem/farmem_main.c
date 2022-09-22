#include<linux/module.h>
#include<linux/kernel.h>
#include <linux/memory_hotplug.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Antoine Kaufmann");
MODULE_DESCRIPTION("Manually exposes specified memory region in the specified "
    "numa node.");
MODULE_VERSION("0.1");

static unsigned long base_addr = 0;
static unsigned long size = 0;
static int nnid = 1;

module_param(base_addr, ulong, 0);
module_param(size, ulong, 0);
module_param(nnid, int, 0);

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

  rc = add_memory_driver_managed(nnid, base_addr, size,
      "System RAM (farmem)", MHP_NONE);
  if (rc) {
    printk(KERN_ALERT "adding memory failed: %d\n", rc);
  }
  node_set_online(nnid);

  return 0;
}

static void __exit farmem_mod_exit(void)
{
  printk(KERN_ALERT "Unloading farmem driver, this is broken\n");
}

module_init(farmem_mod_init);
module_exit(farmem_mod_exit);
