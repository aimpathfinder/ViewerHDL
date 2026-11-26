#!/usr/bin/env python3
"""Expand Yosys JSON cells into a hierarchical, transistor-oriented JSON artifact.

This is an abstract switch-level expansion, not a SKY130 physical extraction. Every
cell receives a status: expanded, hierarchical-instance, or unresolved-macro.
"""
import json, pathlib, re, sys

SUPPLY = ['VPWR', 'VGND', 'VPB', 'VNB']

def scalar(c, *names):
    for name in names:
        value = c.get('connections', {}).get(name)
        if isinstance(value, list) and value:
            return str(value[0])
        if value is not None:
            return str(value)
    return None

def topo(kind, a=None, b=None, y=None, s=None, d=None, internal='n'):
    a, b, y = a or 'A', b or 'B', y or 'Y'
    def p(i, typ, dd, ss, gg): return [f'M{i}', typ, dd, ss, gg, 'VPB' if typ == 'PMOS' else 'VNB']
    if kind == 'NOT':
        return [p(0,'PMOS','VPWR',y,a), p(1,'NMOS',y,'VGND',a)]
    if kind == 'NAND':
        n=f'{internal}1'; return [p(0,'PMOS','VPWR',y,a),p(1,'PMOS','VPWR',y,b),p(2,'NMOS',y,n,a),p(3,'NMOS',n,'VGND',b)]
    if kind == 'NOR':
        n=f'{internal}1'; return [p(0,'PMOS','VPWR',n,a),p(1,'PMOS',n,y,b),p(2,'NMOS',y,'VGND',a),p(3,'NMOS',y,'VGND',b)]
    if kind == 'AND':
        n1,n2=f'{internal}1',f'{internal}2'; return [p(0,'PMOS','VPWR',n1,a),p(1,'PMOS','VPWR',n1,b),p(2,'NMOS',n1,n2,a),p(3,'NMOS',n2,'VGND',b),p(4,'PMOS','VPWR',y,n1),p(5,'NMOS',y,'VGND',n1)]
    if kind == 'OR':
        n1,n2=f'{internal}1',f'{internal}2'; return [p(0,'PMOS','VPWR',n2,a),p(1,'PMOS',n2,n1,b),p(2,'NMOS',n1,'VGND',a),p(3,'NMOS',n1,'VGND',b),p(4,'PMOS','VPWR',y,n1),p(5,'NMOS',y,'VGND',n1)]
    if kind == 'ANDNOT':
        n=f'{internal}1'; return [p(0,'PMOS','VPWR',n,a),p(1,'PMOS','VPWR',n,b),p(2,'NMOS',n,'VGND',a),p(3,'PMOS','VPWR',y,n),p(4,'NMOS',y,'VGND',b)]
    if kind == 'ORNOT':
        n=f'{internal}1'; return [p(0,'PMOS','VPWR',n,a),p(1,'PMOS',n,y,b),p(2,'NMOS',y,'VGND',a),p(3,'NMOS',y,'VGND',b)]
    if kind in ('XOR','XNOR'):
        # Transmission-gate XOR: invert A and B, select B/Bbar with A/Abar.
        ab, bb, out = f'{internal}Abar', f'{internal}Bbar', y if kind == 'XOR' else f'{internal}xor'
        ts = [p(0,'PMOS','VPWR',ab,a),p(1,'NMOS',ab,'VGND',a),p(2,'PMOS','VPWR',bb,b),p(3,'NMOS',bb,'VGND',b)]
        ts += [['M4','PMOS',out,b,ab,'VPB'],['M5','NMOS',out,b,a,'VNB'],['M6','PMOS',out,bb,a,'VPB'],['M7','NMOS',out,bb,ab,'VNB']]
        if kind == 'XNOR': ts += [p(8,'PMOS','VPWR',y,out),p(9,'NMOS',y,'VGND',out)]
        return ts
    if kind == 'MUX':
        sb=f'{internal}Sbar'; ts=[p(0,'PMOS','VPWR',sb,s),p(1,'NMOS',sb,'VGND',s)]
        # Pass-transistor mux with complementary select; explicit TG devices.
        ts += [['M2','PMOS',y,a,s,'VPB'],['M3','NMOS',y,a,sb,'VNB'],['M4','PMOS',y,b,sb,'VPB'],['M5','NMOS',y,b,s,'VNB']]
        return ts
    if kind == 'DFF':
        # Abstract master/slave transmission-gate DFF; controls are C and D.
        q = y; db=f'{internal}Db'; m=f'{internal}M'; cb=f'{internal}Cb'
        ts=[p(0,'PMOS','VPWR',db,d),p(1,'NMOS',db,'VGND',d),p(2,'PMOS','VPWR',cb,s),p(3,'NMOS',cb,'VGND',s)]
        ts += [['M4','PMOS',m,d,cb,'VPB'],['M5','NMOS',m,d,s,'VNB'],['M6','PMOS',m,'VPWR',m,'VPB'],['M7','NMOS',m,'VGND',m,'VNB']]
        ts += [['M8','PMOS',q,m,s,'VPB'],['M9','NMOS',q,m,cb,'VNB'],['M10','PMOS','VPWR',q,q,'VPB'],['M11','NMOS',q,'VGND',q,'VNB']]
        return ts
    return None

def classify(cell):
    t=cell.get('type','')
    if t in ('$_NOT_',): return ('NOT', 'expanded')
    if t in ('$_NAND_',): return ('NAND', 'expanded')
    if t in ('$_NOR_',): return ('NOR', 'expanded')
    if t in ('$_AND_',): return ('AND', 'expanded')
    if t in ('$_OR_',): return ('OR', 'expanded')
    if t in ('$_ANDNOT_',): return ('ANDNOT', 'expanded')
    if t in ('$_ORNOT_',): return ('ORNOT', 'expanded')
    if t in ('$_XOR_',): return ('XOR', 'expanded')
    if t in ('$_XNOR_',): return ('XNOR', 'expanded')
    if t in ('$_MUX_',): return ('MUX', 'expanded')
    if re.match(r'^\$_(DFF|SDFF|DFFE|SDFFE|DFFCE|SDFFCE)', t): return ('DFF', 'abstract-sequential')
    if t.startswith('$paramod') or t in ('mux2','mux4','mux5','mux6','dff','dlatch','counter') or t.endswith('_unit') or t in ('alu','divider','multiplier','register_file','control_unit','main_fsm','csr_exception_handler','extend','load_alignment','store_alignment'):
        return (None, 'hierarchical-instance')
    return (None, 'unresolved-macro')

def expand_module(name, module):
    out_cells={}; counts={'expanded':0,'abstract-sequential':0,'hierarchical-instance':0,'unresolved-macro':0}; transistors=0
    for inst, cell in module.get('cells',{}).items():
        kind,status=classify(cell)
        record={'type':cell.get('type'),'connections':cell.get('connections',{}),'status':status}
        if status in ('expanded','abstract-sequential'):
            pins=cell.get('connections',{})
            a=scalar(cell,'A','A1','D','S0') or f'{inst}.A'; b=scalar(cell,'B','B1','S','S1') or f'{inst}.B'; y=scalar(cell,'Y','Q','X','F') or f'{inst}.Y'; s=scalar(cell,'S','S0','C') or f'{inst}.S'; d=scalar(cell,'D','A') or f'{inst}.D'
            record['topology']=kind; record['transistors']=topo(kind,a=a,b=b,y=y,s=s,d=d,internal=f'{inst}.') or []
            record['device_count']=len(record['transistors']); transistors += len(record['transistors'])
            if status=='abstract-sequential': record['note']='Generic master/slave CMOS topology; reset/set/enable semantics remain in the original cell pins and require technology-specific mapping for physical accuracy.'
        elif status=='hierarchical-instance':
            record['module_ref']=cell.get('type')
            record['note']='Preserved as a hierarchy edge; expand the referenced module in this artifact.'
        else:
            record['note']='No generic topology mapping supplied; retained explicitly so the whole-design output is not mistaken for a complete transistor netlist.'
        out_cells[inst]=record; counts[status]+=1
    return {'name':name,'ports':module.get('ports',{}),'cells':out_cells,'cell_counts':counts,'transistor_count':transistors}

def main(src, dst):
    raw=json.load(open(src)); modules={}; total={'expanded':0,'abstract-sequential':0,'hierarchical-instance':0,'unresolved-macro':0}; devices=0
    for name,module in raw.get('modules',{}).items():
        em=expand_module(name,module); modules[name]=em
        for k,v in em['cell_counts'].items(): total[k]+=v
        devices += em['transistor_count']
    out={'format':'kianv-hierarchical-transistor-netlist-v1','source':pathlib.Path(src).name,'technology':'generic complementary CMOS abstraction; SKY130 physical mapping not asserted','modules':modules,'summary':{'module_count':len(modules),'cell_counts':total,'explicit_transistor_count':devices}}
    pathlib.Path(dst).parent.mkdir(parents=True,exist_ok=True)
    json.dump(out,open(dst,'w'),separators=(',',':'))
    return out['summary']

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: expand_transistors.py input.json output.json')
    print(json.dumps(main(sys.argv[1],sys.argv[2]),sort_keys=True))
