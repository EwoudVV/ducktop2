#include "pack_current.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    /* Synthetic test envelope; this is not an installed-board calibration. */
    const unsigned shunts[]={869,1000,1131}, gains[]={950,1000,1040};
    for (unsigned actual=0;actual<=10000;actual+=7) {
        for (unsigned r=0;r<3;r++) for (unsigned g=0;g<3;g++) {
            int64_t reported=(int64_t)actual*shunts[r]*gains[g]-100000000;
            unsigned code=reported>0 ? (unsigned)(reported/44400000) : 0;
            if (code>=255) continue; /* charger driver rejects saturation */
            int16_t nominal=-(int16_t)((code*444u+9u)/10u);
            int32_t bound=0;
            assert(ec_pack_current_upper_bound(nominal,&bound));
            assert(bound<=0 && (uint32_t)(-bound)>=actual);
        }
    }
    int32_t bound;
    assert(ec_pack_current_upper_bound(0,&bound) && bound<0);
    assert(ec_pack_current_upper_bound(-11278,&bound) && bound < -10000);
    assert(!ec_pack_current_upper_bound(-32768,&bound));
    assert(!ec_pack_current_upper_bound(-500,0));
    assert(ec_pack_current_upper_bound(555,&bound) && bound==555);
    puts("pack current: PASS (under-reading corners, quantization, high code, overflow)");
}
