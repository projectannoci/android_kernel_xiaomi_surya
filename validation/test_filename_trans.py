from pathlib import Path
import sys,subprocess,tempfile
source=Path(sys.argv[1]).read_text();a=source.index('static bool add_filename_trans(',source.index('static bool add_filename_trans(')+1);start=source.index('{',a);b=start+1;depth=1
while depth:
 depth+=(source[b]=='{')-(source[b]=='}');b+=1
function=source[a:b]
stubs=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define KERNEL_VERSION(a,b,c) (((a)<<16)+((b)<<8)+(c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4,14,190)
#define GFP_ATOMIC 0
#define pr_warn(...) ((void)0)
#define pr_err(...) ((void)0)
struct type_datum {unsigned value;};
struct class_datum {unsigned value;};
struct filename_trans {unsigned stype,ttype;unsigned short tclass;const char *name;};
struct filename_trans_datum {unsigned otype;};
struct table {struct filename_trans *key;struct filename_trans_datum *datum;};
struct policydb {int p_types,p_classes;struct table *filename_trans;unsigned filename_trans_ttypes;};
static struct type_datum src={3},tgt={7},def={11},next={13};
static struct class_datum cls={2};
static int alloc_calls,fail_at;
static void *allocation(size_t n){alloc_calls++;if(alloc_calls==fail_at)return NULL;return calloc(1,n);}
#define kmalloc(n,f) allocation(n)
#define kzalloc(n,f) allocation(n)
#define kcalloc(n,s,f) allocation((n)*(s))
#define kfree(p) free((void *)(p))
static char *kstrdup(const char *s,int f){(void)f;char *p=allocation(strlen(s)+1);if(p)strcpy(p,s);return p;}
static void *symtab_search(void *tab,const char *name){(void)tab;if(!strcmp(name,"src"))return &src;if(!strcmp(name,"tgt"))return &tgt;if(!strcmp(name,"def"))return &def;if(!strcmp(name,"next"))return &next;if(!strcmp(name,"cls"))return &cls;return NULL;}
static struct filename_trans_datum *hashtab_search(struct table *t,const struct filename_trans *k){if(t->key&&t->key->stype==k->stype&&t->key->ttype==k->ttype&&t->key->tclass==k->tclass&&!strcmp(t->key->name,k->name))return t->datum;return NULL;}
static int hashtab_insert(struct table *t,struct filename_trans *k,struct filename_trans_datum *d){if(t->key)return -EEXIST;t->key=k;t->datum=d;return 0;}
static int ebitmap_set_bit(unsigned *bits,unsigned index,int value){if(index>31)return -EINVAL;if(value)*bits|=1u<<index;else *bits&=~(1u<<index);return 0;}
'''
main=r'''
int main(void){
 struct table table={0};struct policydb db={.filename_trans=&table};
 assert(add_filename_trans(&db,"src","tgt","cls","def","child"));
 assert(table.key && table.key->stype==3 && table.key->ttype==7 && table.key->tclass==2);
 assert(table.datum->otype==11);
 assert(db.filename_trans_ttypes==(1u<<7));
 assert(add_filename_trans(&db,"src","tgt","cls","next","child"));
 assert(table.datum->otype==13);
 assert(!add_filename_trans(&db,"missing","tgt","cls","def","other"));
 for(int i=1;i<=3;i++){
   struct table empty={0};struct policydb fresh={.filename_trans=&empty};alloc_calls=0;fail_at=i;
   assert(!add_filename_trans(&fresh,"src","tgt","cls","def","child"));
   assert(empty.key==NULL);
 }
 puts("PASS native 4.14 filename transitions: full key, target bitmap, overwrite, missing type and allocation failures");
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'test.c').write_text(stubs+function+main)
 subprocess.run(['gcc','-O0','-ftrivial-auto-var-init=zero','-Wno-unused-function',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
