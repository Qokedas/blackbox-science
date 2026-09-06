#include <bits/stdc++.h>
#define private public
#include <ObjCryst/ObjCryst/PowderPattern.h>
#include <ObjCryst/ObjCryst/Crystal.h>
#include <ObjCryst/ObjCryst/DiffractionDataSingleCrystal.h>
#include <algorithm>
#include <cstdio>
#undef private
using namespace ObjCryst;
struct AccessDiff : PowderPatternDiffraction {
 int matrix(double* out, long npoint,long nref) {
  GetPowderPatternCalc();
  if(nref>long(mvReflProfile.size())) return -1;
  std::fill(out,out+npoint*nref,0.0);
  for(long j=0;j<nref;j++) {
   auto &r=mvReflProfile[j];
   double corr=mIntensityCorr(j)*mMultiplicity(j);
   for(long i=std::max(0L,r.first);i<=std::min(npoint-1,r.last);i++) out[i*nref+j]=r.profile(i-r.first)*corr;
  }
  return long(mvReflProfile.size());
 }
 void setobs(double *v,long n) {
  CrystVector_REAL vv(n);for(long i=0;i<n;i++)vv(i)=v[i];
  mpLeBailData->SetFhklObsSq(vv);
  SetExtractionMode(true,false);
 }
 void march(double frac,double coeff,double h,double k,double l) {mCorrTextureMarchDollase.AddPhase(frac,coeff,h,k,l);}
};
struct AccessCrystal: Crystal {void bumpscale(double scale){mBumpMergeScale=scale; mBumpMergeParClock.Click();}};
extern "C" {
 int bridge_kind(void *ptr) {auto *r=reinterpret_cast<RefinableObj*>(ptr);std::printf("Object: %s %s\n",r->GetClassName().c_str(),r->GetName().c_str()); return sizeof(REAL);}
 int bridge_matrix(void *ptr,double *out,long np,long nr) {auto*d=dynamic_cast<PowderPatternDiffraction*>(reinterpret_cast<RefinableObj*>(ptr));if(!d)return -2;return reinterpret_cast<AccessDiff*>(d)->matrix(out,np,nr);}
 void bridge_setobs(void*ptr,double*v,long n) {auto*d=dynamic_cast<PowderPatternDiffraction*>(reinterpret_cast<RefinableObj*>(ptr));reinterpret_cast<AccessDiff*>(d)->setobs(v,n);}
 void bridge_march(void*ptr,double frac,double coeff,double h,double k,double l) {auto*d=dynamic_cast<PowderPatternDiffraction*>(reinterpret_cast<RefinableObj*>(ptr));reinterpret_cast<AccessDiff*>(d)->march(frac,coeff,h,k,l);}
 void bridge_bumpscale(void*ptr,double scale) {auto*c=dynamic_cast<Crystal*>(reinterpret_cast<RefinableObj*>(ptr));reinterpret_cast<AccessCrystal*>(c)->bumpscale(scale);}
}
