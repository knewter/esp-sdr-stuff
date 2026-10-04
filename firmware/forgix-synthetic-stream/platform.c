/* The builder extracts the reviewed main.c wire primitives unchanged, removes
 * only unused register-loop globals/profile, and uses this explicit encoder.
 * Old bridge admission/whitelists are never changed or used by this profile. */
#include "platform.h"
#define bridge_wire_request fs_source_packet
#include "wire_primitives.inc"
#undef bridge_wire_request
void fs_platform_lifetime(uint64_t until){lifetime_until=until;}
bool fs_platform_configure(uint64_t until){configuration_ready=bridge_configure(until)==BRIDGE_OK;return configuration_ready;}
bool fs_platform_prepare(uint64_t until){return wire_prepare(until)==BRIDGE_OK;}
bool fs_platform_transfer(bool write,uint32_t address,uint32_t *value,uint64_t until){
 bridge_request r={.op=write?BRIDGE_WRITE:BRIDGE_READ,.address=address,.value=write?*value:0};
 uint64_t saved=lifetime_until;if(until<lifetime_until)lifetime_until=until;
 unsigned status=bridge_spi_transaction(&r,value);lifetime_until=saved;
 return status==BRIDGE_OK&&time_us_64()<until;
}
void fs_platform_safe(void){wire_end();}
