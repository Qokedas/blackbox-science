#include <bits/stdc++.h>
#include <ObjCryst/ObjCryst/PowderPattern.h>
#include <ObjCryst/ObjCryst/Crystal.h>
#include <ObjCryst/ObjCryst/ScatteringPower.h>
using namespace ObjCryst;
struct AccessRef:RefinableObj {void attach(RefinableObj &r){AddSubRefObj(r);} void detach(RefinableObj&r){RemoveSubRefObj(r);}};
struct PackingLSQ:RefinableObj {
 Crystal *c;
 std::vector<long> ii,jj;
 std::vector<double> rt,tt,limit;
 mutable CrystVector_REAL obs,calc,wgt;
 PackingLSQ(Crystal *cr,long n,long *i,long *j,double *r,double *t,double *l,double *w):c(cr) {
  SetName("Heavy_atom_packing_restraints");ii.assign(i,i+n);jj.assign(j,j+n);rt.assign(r,r+9*n);tt.assign(t,t+3*n);limit.assign(l,l+n);obs.resize(n);calc.resize(n);wgt.resize(n);
  for(long k=0;k<n;k++){obs(k)=0;calc(k)=0;wgt(k)=w[k];}
  AddSubRefObj(*c);
 }
 virtual const std::string &GetClassName()const {static const std::string name="PackingLSQ";return name;}
 virtual unsigned int GetNbLSQFunction()const{return 1;}
 virtual const CrystVector_REAL& GetLSQObs(const unsigned int)const{return obs;}
 virtual const CrystVector_REAL& GetLSQWeight(const unsigned int)const{return wgt;}
 virtual const CrystVector_REAL& GetLSQCalc(const unsigned int)const {
  auto &sc=c->GetScatteringComponentList();auto &m=c->GetOrthMatrix();
  for(size_t k=0;k<ii.size();k++){
   auto &a=sc(ii[k]);auto &b=sc(jj[k]);double x=a.mX-(rt[9*k]*b.mX+rt[9*k+1]*b.mY+rt[9*k+2]*b.mZ+tt[3*k]);
   double y=a.mY-(rt[9*k+3]*b.mX+rt[9*k+4]*b.mY+rt[9*k+5]*b.mZ+tt[3*k+1]);
   double z=a.mZ-(rt[9*k+6]*b.mX+rt[9*k+7]*b.mY+rt[9*k+8]*b.mZ+tt[3*k+2]);
   x-=std::round(x);y-=std::round(y);z-=std::round(z);double best=1.e100;
   for(int sx=-1;sx<=1;sx++)for(int sy=-1;sy<=1;sy++)for(int sz=-1;sz<=1;sz++){
    double dx=x+sx,dy=y+sy,dz=z+sz;
    double u=m(0,0)*dx+m(0,1)*dy+m(0,2)*dz;
    double v=m(1,0)*dx+m(1,1)*dy+m(1,2)*dz;
    double w=m(2,0)*dx+m(2,1)*dy+m(2,2)*dz;
    best=std::min(best,u*u+v*v+w*w);
   }
   calc(k)=std::max(0.,limit[k]-std::sqrt(best+1.e-18));
  }
  return calc;
 }
 double cost()const{auto &v=GetLSQCalc(0);double cost=0;for(long k=0;k<v.numElements();k++)cost+=v(k)*v(k)*wgt(k);return cost;}
};
extern "C" {
void *packing_attach(void *pp,void *cc,long n,long*i,long*j,double*r,double*t,double*l,double*w){
 auto *c=dynamic_cast<Crystal*>(reinterpret_cast<RefinableObj*>(cc));if(!c)return nullptr;
 auto *p=reinterpret_cast<AccessRef*>(pp);auto *rest=new PackingLSQ(c,n,i,j,r,t,l,w);p->attach(*rest);return rest;
}
double packing_cost(void *p){return reinterpret_cast<PackingLSQ*>(p)->cost();}
void packing_detach(void *pp,void*rr){auto *p=reinterpret_cast<AccessRef*>(pp);auto *r=reinterpret_cast<PackingLSQ*>(rr);p->detach(*r);delete r;}
}
