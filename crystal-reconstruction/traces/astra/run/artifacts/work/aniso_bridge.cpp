#include <ObjCryst/ObjCryst/PowderPattern.h>
#include <ObjCryst/ObjCryst/ReflectionProfile.h>
#include <cmath>
using namespace ObjCryst;
extern "C" int bridge_aniso(void* ptr) {
 auto*d=dynamic_cast<PowderPatternDiffraction*>(reinterpret_cast<RefinableObj*>(ptr));if(!d)return -1;
 auto&old=d->GetProfile();double u=old.GetPar("U").GetValue(),v=old.GetPar("V").GetValue(),w=old.GetPar("W").GetValue();
 double eta0=old.GetPar("Eta0").GetValue(),eta1=old.GetPar("Eta1").GetValue(),a0=old.GetPar("Asym0").GetValue(),a1=old.GetPar("Asym1").GetValue(),a2=old.GetPar("Asym2").GetValue();
 auto*r=new ReflectionProfilePseudoVoigtAnisotropic();
 r->SetProfilePar(w,u,v,0.,std::sqrt(std::max(w,1.e-9)),std::sqrt(std::max(u,1.e-9)),0,0,0,0,0,0,eta0,eta1,a0,a1,a2);
 d->SetProfile(r);return 0;
}
