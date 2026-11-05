/* SPDX-License-Identifier: GPL-2.0-only
 * Singularity recovery helper. Freestanding ARM EABI, no libc dependencies.
 * SHA-256 is supplied by the existing BusyBox sha256sum applet.
 * Only an existing unsigned boot hash descriptor is updated. Signed metadata
 * is rejected; flags, keys, rollback counters and other descriptors are kept.
 */
typedef unsigned char u8;
typedef unsigned int u32;
#define MAX_IMAGE (512U * 1024U * 1024U)
static char **environment;
static u8 metadata[65536], chunk[16384], footer[64], zeroes[64];

static long sys4(long n, long a, long b, long c, long d)
{
    register long r0 __asm__("r0")=a;
    register long r1 __asm__("r1")=b;
    register long r2 __asm__("r2")=c;
    register long r3 __asm__("r3")=d;
    register long r7 __asm__("r7")=n;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1),"r"(r2),"r"(r3),"r"(r7) : "memory","cc");
    return r0;
}
static u32 length(const char *s){u32 n=0;while(s[n])n++;return n;}
static void finish(int status) __attribute__((noreturn));
static void finish(int status){sys4(1,status,0,0,0);for(;;){}}
static void fail(const char *s){sys4(4,2,(long)s,length(s),0);sys4(4,2,(long)"\n",1,0);finish(1);}
static int equal(const u8 *a,const u8 *b,u32 n){while(n--)if(*a++!=*b++)return 0;return 1;}
static u32 be32(const u8 *p){return (u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
static u32 small64(const u8 *p){if(be32(p))fail("AVB offset exceeds supported size");return be32(p+4);}
static void put32(u8 *p,u32 v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static void put64(u8 *p,u32 v){put32(p,0);put32(p+4,v);}
static void closefd(int fd){sys4(6,fd,0,0,0);}
static void seekto(int fd,u32 offset){if(sys4(19,fd,offset,0,0)!=(long)offset)fail("Image seek failed");}
static int io(int fd,u8 *p,u32 n,int write_mode)
{
    while(n){long r=sys4(write_mode?4:3,fd,(long)p,n,0);if(r==-4)continue;if(r<=0)return 0;p+=r;n-=r;}return 1;
}
static void readat(int fd,u32 off,u8 *p,u32 n){seekto(fd,off);if(!io(fd,p,n,0))fail("Image read failed");}
static void writeat(int fd,u32 off,u8 *p,u32 n){seekto(fd,off);if(!io(fd,p,n,1))fail("Image write failed");}
static u32 number(const char *s)
{
    u32 n=0;if(!*s)fail("Missing partition size");
    while(*s){u32 d=(u8)*s++-'0';if(d>9||n>53687091U||(n==53687091U&&d>2))fail("Invalid partition size");n=n*10+d;}
    return n;
}
static int nibble(u8 c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
static void digest(int fd,const char *busybox,const u8 *salt,u32 salt_size,u32 image_size,u8 *result)
{
    int input[2],output[2],status=0;u8 text[96];u32 used=0,left=image_size;long pid,r;int ok=1;
    if(sys4(42,(long)input,0,0,0)<0||sys4(42,(long)output,0,0,0)<0)fail("Hash pipe failed");
    pid=sys4(2,0,0,0,0);if(pid<0)fail("Hash fork failed");
    if(!pid){
        char *argv[3];argv[0]=(char*)busybox;argv[1]="sha256sum";argv[2]=0;
        closefd(fd);
        if(sys4(63,input[0],0,0,0)<0||sys4(63,output[1],1,0,0)<0)finish(127);
        if(input[0]!=0&&input[0]!=1)closefd(input[0]);
        if(input[1]!=0&&input[1]!=1)closefd(input[1]);
        if(output[0]!=0&&output[0]!=1)closefd(output[0]);
        if(output[1]!=0&&output[1]!=1)closefd(output[1]);
        sys4(11,(long)busybox,(long)argv,(long)environment,0);finish(127);
    }
    closefd(input[0]);closefd(output[1]);seekto(fd,0);
    if(salt_size&&!io(input[1],(u8*)salt,salt_size,1))ok=0;
    while(left&&ok){u32 n=left>sizeof(chunk)?sizeof(chunk):left;if(!io(fd,chunk,n,0)||!io(input[1],chunk,n,1))ok=0;left-=n;}
    closefd(input[1]);
    while(used<sizeof(text)){
        r=sys4(3,output[0],(long)(text+used),sizeof(text)-used,0);
        if(r==-4)continue;if(r<0){ok=0;break;}if(!r)break;used+=r;
    }
    closefd(output[0]);
    do{r=sys4(114,pid,(long)&status,0,0);}while(r==-4);
    if(!ok||r!=pid||status||used<64)fail("BusyBox hash failed");
    for(u32 i=0;i<32;i++){int a=nibble(text[2*i]),b=nibble(text[2*i+1]);if(a<0||b<0)fail("Invalid hash output");result[i]=(a<<4)|b;}
}
static void pad(int fd,u32 current,u32 target,int has_footer)
{
    if(current<target){
        if(has_footer){writeat(fd,current-64,zeroes,64);writeat(fd,target-64,footer,64);}
        else writeat(fd,target-1,zeroes,1);
    }
    if(sys4(118,fd,0,0,0)<0)fail("Image fsync failed");
}
void start_main(u32 *stack) __attribute__((used,noreturn));
void start_main(u32 *stack)
{
    u32 argc=stack[0];char **argv=(char**)&stack[1];int fd;long end;
    u32 current,target,image_size,position,meta_size,aux_size,desc_off,desc_size,at,limit;
    u32 hash_at=0,digest_at=0,salt_at=0,salt_size=0,hash_count=0;u8 hash[32],magic[8];
    if(argc!=4)fail("Usage: avbfix IMAGE BUSYBOX PARTITION_BYTES");
    environment=argv+argc+1;target=number(argv[3]);
    fd=sys4(5,(long)argv[1],2,0,0);if(fd<0)fail("Cannot open repacked image");
    end=sys4(19,fd,0,2,0);
    if(end<64||(u32)end>MAX_IMAGE||target<(u32)end||target>MAX_IMAGE)fail("Repacked image exceeds partition");
    current=end;readat(fd,0,magic,8);if(!equal(magic,(const u8*)"ANDROID!",8))fail("Not an Android boot image");
    readat(fd,current-64,footer,64);
    if(!equal(footer,(const u8*)"AVBf",4)){pad(fd,current,target,0);closefd(fd);finish(0);}
    if(be32(footer+4)!=1)fail("Unsupported AVB footer");
    image_size=small64(footer+12);position=small64(footer+20);meta_size=small64(footer+28);
    if(!image_size||image_size>position||position>current-64||meta_size>current-64-position||meta_size<256||meta_size>sizeof(metadata))fail("Invalid AVB bounds");
    readat(fd,position,metadata,meta_size);
    if(!equal(metadata,(const u8*)"AVB0",4))fail("Invalid vbmeta magic");
    if(be32(metadata+28)||small64(metadata+12))fail("Signed vbmeta needs its signing key; refusing modification");
    aux_size=small64(metadata+20);desc_off=small64(metadata+96);desc_size=small64(metadata+104);
    if(aux_size>meta_size-256||desc_off>aux_size||desc_size>aux_size-desc_off)fail("Invalid descriptor bounds");
    at=256+desc_off;limit=at+desc_size;
    while(at<limit){
        u32 tag,following,stop;
        if(limit-at<16)fail("Truncated descriptor");
        tag=small64(metadata+at);following=small64(metadata+at+8);
        if(following>limit-at-16)fail("Invalid descriptor size");stop=at+16+following;
        if(tag==2){
            u32 name_size,salt_len,digest_size,p;
            if(stop-at<132)fail("Truncated boot hash descriptor");
            name_size=be32(metadata+at+56);salt_len=be32(metadata+at+60);digest_size=be32(metadata+at+64);p=at+132;
            if(name_size!=4||salt_len>1024||digest_size!=32||stop-p<4||salt_len>stop-p-4||digest_size>stop-p-4-salt_len)fail("Invalid boot hash fields");
            if(!equal(metadata+p,(const u8*)"boot",4)||!equal(metadata+at+24,(const u8*)"sha256\0",7))fail("Unsupported hash descriptor");
            hash_at=at;salt_at=p+4;salt_size=salt_len;digest_at=salt_at+salt_size;hash_count++;
        }
        at=stop;
    }
    if(hash_count!=1)fail("Expected one unsigned boot hash descriptor");
    digest(fd,argv[2],metadata+salt_at,salt_size,image_size,hash);
    put64(metadata+hash_at+16,image_size);
    for(u32 i=0;i<32;i++)metadata[digest_at+i]=hash[i];
    writeat(fd,position,metadata,meta_size);pad(fd,current,target,1);closefd(fd);finish(0);
}
__attribute__((naked,noreturn)) void _start(void)
{
    __asm__ volatile("mov r0, sp\n b start_main");
}
