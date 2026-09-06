subroutine fcj(n,x,pos,sig,gam,shl,out) bind(C,name='fcj')
use iso_c_binding
implicit none
integer(c_int),value :: n
real(c_double),intent(in) :: x(n)
real(c_double),value :: pos,sig,gam,shl
real(c_double),intent(out)::out(n,5)
integer i
real f,dt,ds,dg,dh,dl
real a,b,c,d,e
b=real(pos*100d0);c=real(sig);d=real(gam);e=real(shl/2d0)
do i=1,n
 a=real((x(i)-pos)*100d0)
 call PSVFCJO(a,b,c,d,e,e,f,dt,ds,dg,dl,dh)
 out(i,1)=dble(f)*100d0
 out(i,2)=dble(dt)*10000d0
 out(i,3)=dble(ds)*100d0
 out(i,4)=dble(dg)*100d0
 out(i,5)=dble(dl+dh)*50d0
end do
end subroutine fcj
