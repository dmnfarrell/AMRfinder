"""
    Various methods for bacterial genomics.
    Created Nov 2019
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import print_function
import sys,os,subprocess,glob,shutil,re
from collections import OrderedDict, defaultdict
import platform
from Bio import Entrez
Entrez.email = 'A.N.Other@example.com'
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio import SeqIO
from Bio import Phylo, AlignIO
import urllib
import numpy as np
import pandas as pd

home = os.path.expanduser("~")
module_path = os.path.dirname(os.path.abspath(__file__)) #path to module
datadir = os.path.join(module_path, 'data')
featurekeys = ['type','protein_id','locus_tag','gene','db_xref',
               'product', 'note', 'translation','pseudo','start','end','strand']

config_path = os.path.join(home,'.config','pathogenie')
bin_path = os.path.join(config_path, 'binaries')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """

    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_cmd(cmd):
    """Get windows version of a command if required"""

    if getattr(sys, 'frozen', False):
        cmd = tools.resource_path('bin/%s.exe' %cmd)
    elif platform.system() == 'Windows':
        cmd = os.path.join(bin_path, '%s.exe' %cmd)
    return cmd

def fetch_binaries():
    """Get windows binaries -- windows only"""

    url = "https://github.com/dmnfarrell/pathogenie/raw/master/win_binaries/"
    path = os.path.join(config_path, 'binaries')
    os.makedirs(path, exist_ok=True)
    names = ['aragorn.exe','blastn.exe','blastp.exe','makeblastdb.exe',
            'hmmscan.exe','hmmpress.exe','prodigal.exe','msys-2.0.dll','clustalw.exe']
    for n in names:
        filename = os.path.join(path,n)
        if os.path.exists(filename):
            continue
        link = os.path.join(url,n)
        print (filename,link)
        urllib.request.urlretrieve(link, filename)
    return

def read_length_dist(df):

    df['length'] = df.seq.str.len()
    bins = np.linspace(1,df.length.max(),df.length.max())
    x = np.histogram(df.length,bins=bins)
    return x

def dataframe_to_fasta(df, seqkey='translation', idkey='locus_tag',
                     descrkey='description',
                     outfile='out.faa'):
    """DataFrame of protein features to a fasta file"""

    seqs=[]
    for i,row in df.iterrows():
        if descrkey in df.columns:
            d=row[descrkey]
        else:
            d=''

        if type(row[seqkey]) is not str:
            continue
        rec = SeqRecord(Seq(row[seqkey]), id=row[idkey], description=d)
        seqs.append(rec)
    SeqIO.write(seqs, outfile, "fasta")
    return outfile

def dataframe_to_seqrecords(df, seqkey='sequence', idkey='id', desckey='description',
                            alphabet=None):
    """Dataframe to list of Bio.SeqRecord objects"""

    #from Bio.Alphabet import IUPAC
    if alphabet=='protein':
        alphabet = IUPAC.protein
    seqs=[]
    for i,r in df.iterrows():
        s = SeqRecord(Seq(r[seqkey]),id=r[idkey],description=r[desckey])
        seqs.append(s)
    return seqs

def genbank_to_dataframe(infile, cds=False):
    """Get genome records from a genbank file into a dataframe
      returns a dataframe with a row for each cds/entry"""

    recs = list(SeqIO.parse(infile,'genbank'))
    res=[]
    for rec in recs:
        df = features_to_dataframe(rec.features, cds)
        res.append(df)
    res = pd.concat(res)
    return res

def check_tags(df):
    """Check genbank tags to make sure they are not empty.
    Args: pandas dataframe
    """

    def replace(x):
        if pd.isnull(x.locus_tag):
            return x.gene
        else:
            return x.locus_tag
    df['locus_tag'] = df.apply(replace,1)
    return df

def gff_to_features(gff_file):
    """Get features from gff file"""

    if gff_file is None or not os.path.exists(gff_file):
        return
    from BCBio import GFF
    in_handle = open(gff_file,'r')
    rec = list(GFF.parse(in_handle))[0]
    in_handle.close()
    return rec.features

def save_gff(recs, outfile):

    f = open(outfile,'w')
    from BCBio import GFF
    for r in recs:
        GFF.write([recs[r]], f)
    return

def features_to_dataframe(features, cds=False, id=''):
    """Get features from a biopython seq record object into a dataframe
    Args:
        features: bio seqfeatures
       returns: a dataframe with a row for each cds/entry.
      """

    featurekeys = []
    allfeat = []
    allquals = []
    for (item, f) in enumerate(features):
        x = f.__dict__
        quals = f.qualifiers
        x.update(quals)
        d = {}
        d['start'] = f.location.start
        d['end'] = f.location.end
        d['strand'] = f.location.strand
        d['id'] = id
        d['feat_type'] = f.type
        for i in quals:
            if i in x:
                if type(x[i]) is list:
                    d[i] = x[i][0]
                else:
                    d[i] = x[i]
        allfeat.append(d)
        for q in quals.keys():
            if q not in allquals:
                allquals.append(q)
    quals = list(allquals)+['id','start','end','strand','feat_type']
    df = pd.DataFrame(allfeat,columns=quals)
    if 'translation' in df.keys():
        df['length'] = df.translation.astype('str').str.len()
    if cds == True:
        df = df[df.feat_type=='CDS']
    if len(df) == 0:
        print ('ERROR: genbank file return empty data, check that the file contains protein sequences '\
               'in the translation qualifier of each protein feature.' )
    return df

def records_to_dataframe(recs):
    """Convert multiple seqrecords features to single dataframe"""

    res=[]
    for rec in recs:
        df = features_to_dataframe(rec.features, id=rec.id)
        res.append(df)
    res=pd.concat(res, sort=False)
    return res

def fasta_to_dataframe(infile, header_sep=None, key='name', seqkey='sequence'):
    """Get fasta proteins into dataframe"""

    recs = SeqIO.parse(infile,'fasta')
    keys = [key,seqkey,'description']
    data = [(r.name,str(r.seq),str(r.description)) for r in recs]
    df = pd.DataFrame(data,columns=(keys))
    df['type'] = 'CDS'
    #fix bad names
    if header_sep not in ['',None]:
        df[key] = df[key].apply(lambda x: x.split(header_sep)[0],1)
    #df[key] = df[key].str.replace('|','_')
    return df

def get_fasta_info(filename):
    """Get fasta file info"""

    df = fasta_to_dataframe(filename)
    name = os.path.splitext(os.path.basename(filename))[0]
    d = {'label':name,'filename':filename, 'contigs':len(df)}
    return d

def collapse_sequences(seqs, refrec):
    """Get unique sequences from list of seqrecords"""

    unique = {}
    counts = {}
    #unique[refrec.seq] = 'ref'
    l = len(refrec.seq)
    for seq in seqs:
        if not seq.seq in counts:
            counts[seq.seq] = 1
        else:
            counts[seq.seq] += 1
        if len(seq.seq)<l-10 or len(seq.seq)>l+5 or 'X' in seq.seq:
            continue
        if not seq.seq in unique:
            unique[seq.seq] = seq.id
    new = []
    for k in unique:
        new.append(SeqRecord(k,id=unique[k]))
    return new, counts

def make_blast_database(filename, dbtype='nucl'):
    """Create a blast db from fasta file"""

    cmd = get_cmd('makeblastdb')
    cline = '%s -dbtype %s -in %s' %(cmd,dbtype,filename)
    subprocess.check_output(cline, shell=True)
    return

def local_blast(database, query, output=None, maxseqs=50, evalue=0.001,
                    compress=False, cmd='blastn', threads=2, show_cmd=False, **kwargs):
    """Blast a local database.
    Args:
        database: local blast db name
        query: sequences to query, list of strings or Bio.SeqRecords
    Returns:
        pandas dataframe with top blast results
    """

    if output == None:
        output = os.path.splitext(query)[0]+'_blast.txt'
    cmd = get_cmd(cmd)

    from Bio.Blast.Applications import NcbiblastxCommandline
    outfmt = '"6 qseqid sseqid qseq sseq pident qcovs length mismatch gapopen qstart qend sstart send evalue bitscore stitle"'
    cline = NcbiblastxCommandline(query=query, cmd=cmd, db=database,
                                 max_target_seqs=maxseqs,
                                 outfmt=outfmt, out=output,
                                 evalue=evalue, num_threads=threads, **kwargs)
    if show_cmd == True:
        print (cline)
    stdout, stderr = cline()
    return

def get_blast_results(filename):
    """
    Get blast results into dataframe. Assumes column names from local_blast method.
    Returns:
        dataframe
    """

    cols = ['qseqid','sseqid','qseq','sseq','pident','qcovs','length','mismatch','gapopen',
            'qstart','qend','sstart','send','evalue','bitscore','stitle']
    res = pd.read_csv(filename, names=cols, sep='\t')
    return res

def blast_sequences(database, seqs, labels=None, **kwargs):
    """
    Blast a set of sequences to a local or remote blast database
    Args:
        database: local or remote blast db name
                  'nr', 'refseq_protein', 'pdb', 'swissprot' are valide remote dbs
        seqs: sequences to query, list of strings or Bio.SeqRecords
        labels: list of id names for sequences, optional but recommended
    Returns:
        pandas dataframe with top blast results
    """

    remotedbs = ['nr','refseq_protein','pdb','swissprot']
    res = []
    if labels is None:
        labels = seqs
    recs=[]

    for seq, name in zip(seqs,labels):
        if type(seq) is not SeqRecord:
            rec = SeqRecord(Seq(seq),id=name)
        else:
            rec = seq
            name = seq.id
        recs.append(rec)
    SeqIO.write(recs, 'tempseq.fa', "fasta")
    if database in remotedbs:
        remote_blast(database, 'tempseq.fa', **kwargs)
    else:
        local_blast(database, 'tempseq.fa', **kwargs)
    df = get_blast_results(filename='tempseq_blast.txt')
    #merge original seqs
    queries = fasta_to_dataframe('tempseq.fa').reset_index()
    df = df.merge(queries, left_on='qseqid', right_on='name', how='left')
    return df

def clustal_alignment(filename=None, seqs=None, command="clustalw"):
    """Align sequences with clustal"""

    if filename == None:
        filename = 'temp.faa'
        SeqIO.write(seqs, filename, "fasta")
    name = os.path.splitext(filename)[0]
    command = get_cmd('clustalw')

    from Bio.Align.Applications import ClustalwCommandline
    cline = ClustalwCommandline(command, infile=filename)
    #print (cline)
    stdout, stderr = cline()
    align = AlignIO.read(name+'.aln', 'clustal')
    return align

def muscle_alignment(filename=None, seqs=None):
    """Align sequences with muscle"""

    if filename == None:
        filename = 'temp.faa'
        SeqIO.write(seqs, filename, "fasta")
    name = os.path.splitext(filename)[0]
    from Bio.Align.Applications import MuscleCommandline
    cline = MuscleCommandline(input=filename, out=name+'.txt')
    stdout, stderr = cline()
    align = AlignIO.read(name+'.txt', 'fasta')
    return align

def plot_tree(dend_file, name='', ax=None):
    """Plot phylo tree"""

    from Bio import Phylo
    import pylab as plt
    if ax==None:
        f,ax=plt.subplots(1,1,figsize=(12,8))
    tree = Phylo.read(dend_file, "newick")
    ax.set_title(name)
    Phylo.draw(tree,axes=ax)
    ax.axis('off')
    return

def align_nucmer(file1, file2):
    cmd='nucmer --maxgap=500 --mincluster=100 --coords -p nucmer %s %s' %(file1, file2)
    print (cmd)
    subprocess.check_output(cmd,shell=True)
    df = read_nucmer_coords('nucmer.coords')
    return df

def read_nucmer_coords(cfile):
    cols=['S1','E1','S2','E2','LEN 1','LEN 2','IDENT','TAG1','TAG2']
    a=pd.read_csv(cfile,sep='[\s|]+',skiprows=5,names=cols,engine='python')
    a = a.sort_values(by='TAG2',ascending=False)
    return a

def align_reads(file1, file2, idx, out):
	"""align reads to ref"""

    #cmd = 'bowtie2 -x %s -1 %s -2 %s --threads 6 | samtools view -bS - > %s' %(idx,files[0],files[1],out)
	cmd = 'bwa mem -M -t 8 %s %s %s | samtools view -bS - > %s' %(idx,files[0],files[1],out)
	if not os.path.exists(out):
		print (cmd )
		subprocess.check_output(cmd, shell=True)
	return

def align_info(bamfile):

    cmd = 'samtools flagstat %s' %bamfile
    temp=subprocess.check_output(cmd, shell=True)
    print (temp)
    return

def variants_call(name, ref, out):

    bamfile = '%s/%s.bam' %(out,name)
    cmd = 'samtools sort {b} > {b}.sorted && samtools index {b}.sorted'.format(b=bamfile)
    print (cmd)
    #subprocess.check_output(cmd, shell=True)
    cmd = 'samtools mpileup -uf genomes/{r}.fa {b}.sorted | bcftools call -mv \
    > {o}/{n}.vcf'.format(b=bamfile,n=name,r=ref,o=out)
    print (cmd)
    #subprocess.check_output(cmd, shell=True)
    cmd = 'bedtools intersect -a {gff} -b {o}/{n}.vcf -wa -u > {o}/{n}_variants.bed'.format(n=name,r=ref,gff=gff,o=out)
    print (cmd)

def search_genbank(term='', filt=None):
    request = Entrez.esearch(db="nuccore", term=term, field="title", FILT=filt, rettype='xml')
    result = Entrez.read(request)
    idlist = result['IdList']
    return idlist

def retrieve_entrez_annotation(id_list):

    """Annotates Entrez Gene IDs using Bio.Entrez, in particular epost (to
    submit the data to NCBI) and esummary to retrieve the information.
    Returns a list of dictionaries with the annotations."""

    request = Entrez.epost("nucleotide",id=",".join(id_list))
    try:
        result = Entrez.read(request)
    except RuntimeError as e:
        #FIXME: How generate NAs instead of causing an error with invalid IDs?
        print ("An error occurred while retrieving the annotations.")
        print ("The error returned was %s" % e)
        sys.exit(-1)

    webEnv = result["WebEnv"]
    queryKey = result["QueryKey"]
    data = Entrez.esummary(db="gene", webenv=webEnv, query_key =
            queryKey)
    annotations = Entrez.read(data)
    print ("Retrieved %d annotations for %d genes" % (len(annotations),
            len(id_list)))
    return annotations

def retrieve_sequences(id_list):
    """get entrez sequence"""

    request = Entrez.epost("nucleotide",id=",".join(id_list))
    result = Entrez.read(request)
    webEnv = result["WebEnv"]
    queryKey = result["QueryKey"]
    handle = Entrez.efetch(db="nucleotide",retmode="xml", webenv=webEnv, query_key=queryKey)
    recs={}
    for r in Entrez.parse(handle):
        recs[r['GBSeq_primary-accession']] = r
    return recs

def recs_to_fasta(recs, outfile):

    res=[]
    for i in recs:
        r=recs[i]
        res.append( [r['GBSeq_primary-accession'],r['GBSeq_sequence'],r['GBSeq_definition']] )
    df=pd.DataFrame(res,columns=['id','sequence','description'])
    dataframe_to_fasta(df,outfile=outfile,seqkey='sequence',idkey='id')
    return

def recs_to_genbank(recs, outfile):
    """Write seqrecords to genbank file"""

    handle = open(outfile,'w+')
    for rec in recs:
        #rec = recs[i]
        SeqIO.write(rec, handle, "genbank")
    handle.close()
    return

def recs_to_gff(recs, outfile):

    f = open(outfile,'w+')
    from BCBio import GFF
    for rec in recs:
        print (rec)
        GFF.write([rec], f)
    return

def get_gilist(accs):

    query  = " ".join(accs)
    handle = Entrez.esearch(db="nucleotide",term=query,retmax=10000)
    gilist = Entrez.read(handle)['IdList']
    return gilist

def read_blast_nr(filename):

    blastcols = ['contig','gid','name','accession','pident','length',
                 '?', '61', 'qstart', 'qend', 'sstart', 'send',
                  'evalue', 'score']
    bl = pd.read_csv('909D3A_blast_nr.csv',names=blastcols)
    #print bl[bl.contig=='NODE_1_length_485821_cov_65.8942']
    g = bl.groupby(['contig','accession']).agg({'score':np.sum,'length':np.sum,'pident':np.max})
    g = g.sort_values('score',ascending=False).reset_index()
    return g

#prokka and roary utils

def get_gene_name(x):
    p=str(x['product'])
    if x.gene is np.nan:
        s=p.split(':')[0][:35]
        if s == None:
            s=p.split(';')[0][:35]
        return s
    return x.gene

def get_aro(x):
    x=str(x)
    if 'ARO' in x:
        s=x[x.find("[")+1:x.find("]")].split(';')[0]
        return s

def get_product(x):
    x=str(x)
    s = x.split(';')[0]
    #print s
    return s

def prokka_results(path,names):
    """parse prokka results for multiple files"""

    res=[]
    for n in names:
        f = '%s/%s/%s.tsv' %(path,n,n)
        df=pd.read_csv(f,sep='\t')
        df['isolate'] = n
        print (n, len(df))
        #print df
        res.append(df)
    res=pd.concat(res)
    res['gene'] = res.apply( lambda x: get_gene_name(x),1)
    res['cat'] = res['product'].apply(lambda x: apply_cat(x))
    #res['aro'] = res['product'].apply(lambda x: get_aro(x))
    res['fam'] = res['product'].apply(lambda x: get_product(x))
    return res

def apply_cat(x):
    keys=['ARO','efflux','adhesin','LEE','porin','stress',
          'secretion system', 'bacteriophage',
          'membrane','transmembrane','prophage','secreted','IS','insertion','transposase','integrase',
          'virulence','protease','stress','toxic','phage','kinase','phosphatase','transferase',
          'hypothetical','membrane','binding','ribosomal rna','ribosomal','trna','methyltransferase',
          'polymerase','transcription','lipoprotein','protease','hydrolase','zinc',
          'cell division','cell cycle','cytoplasm','endosome','dna-binding']
    for i in keys:
        if x is np.nan: return
        if i in x.lower():
            return i
    return 'other'

def genes_clustermap(x,xticklabels=0,title=''):
    """plot cluster map of genes"""

    from matplotlib.colors import ListedColormap, LogNorm
    #x = x[x.sum(1)>=1]
    sys.setrecursionlimit(20000)
    clrs = ["lightgray", "blue"]
    t_cmap = ListedColormap(sns.color_palette(clrs).as_hex())
    if len(x)>50:
        yticklabels=0
    if len(x.T)>50:
        xticklabels=0
    cg=sns.clustermap(x,xticklabels=xticklabels,yticklabels=1,cmap=t_cmap,figsize=(12,7))
    cg.fig.suptitle(title)
    cg.fig.subplots_adjust(right=0.8)
    return

# annotation record functions

def get_annotations_dataframe(annotations):
    """Get dataframe from all annotation records"""

    x=[]
    for name in annotations:
        recs = annotations[name]
        featsdf = records_to_dataframe(recs)
        featsdf['sample'] = name
        x.append(featsdf)
    df = pd.concat(x)
    return df

def get_nucleotide_sequence_from_record(self, recs, chrom, start, end):

    recs = SeqIO.to_dict(recs)
    rec = recs[chrom]
    new = rec[start:end]
    new.id = name
    new.description = chrom+':'+str(start)+'-'+str(end)
    return new

def create_gene_matrix(annotations):
    """Presence/absence matrix of gene features across a set of annotations"""

    x = []
    for name in annotations:
        recs = annotations[name]
        featsdf = records_to_dataframe(recs)
        featsdf['sample'] = name
        x.append(featsdf)
    x = pd.concat(x)
    m = pd.pivot_table(x, index='sample', columns=['gene','product'], values='start')
    m[m.notnull()] = 1
    m = m.fillna(0)
    m = m.T.reset_index()
    return m

#phylogenetic tree functions

def build_tree(aln, kind='nj'):
    """Build a tree with bio.phylo module"""

    from Bio.Phylo.TreeConstruction import DistanceCalculator,DistanceTreeConstructor
    calculator = DistanceCalculator('identity')
    dm = calculator.get_distance(aln)
    constructor = DistanceTreeConstructor()
    tree = constructor.nj(dm)
    return dm, tree

def clear_clades(tree):
    """Clear inner labels for clades in bio.pyhlo tree"""

    names = {}
    for idx, clade in enumerate(tree.find_clades()):
        if 'Inner' in clade.name :
            clade.name = ''

        names[clade.name] = clade
    return names

def draw_tree(tree, root=None, labels=None, clear=True, title='', ax=None):
    """Draw phylogenetic tree with biopython"""

    import pylab as plt
    if ax == None:
        fig,ax=plt.subplots(figsize=(10,8))
    if clear == True:
        try:
            clear_clades(tree)
        except:
            pass
    if root != None:
        tree.root_with_outgroup(root)
    if labels != None:
        for clade in tree.get_terminals():
            key = clade.name
            if key in labels:
                clade.name = '%s; %s' %(key,labels[key])
                #clade.name = labels[key]

    Phylo.draw(tree,axes=ax,axis=('off',), do_show=False, label_colors=None,
                branch_labels=None, show_confidence=False)
    ax.set_title(title,fontsize=16)
    ax.set_frame_on(False)
    return

def tree_from_distance_matrix(X):
    """Distance matrix to phylo tree"""
    
    from Bio import Phylo
    from Bio.Phylo.TreeConstruction import DistanceMatrix,DistanceTreeConstructor
    from Bio.Cluster import distancematrix

    names = list(X.index)
    if type(X) is pd.DataFrame:
        X = X.values
    mat = distancematrix(X)

    #print (names)
    #names = [i[16:] for i in names]
    new=[]
    for i in mat:
        new.append(np.insert(i, 0, 0).tolist())

    dm = DistanceMatrix(names,new)
    constructor = DistanceTreeConstructor()
    tree = constructor.nj(dm)
    #Phylo.draw_ascii(tree,file=open('temp.txt','w'))
    return tree

def ml_tree(aln, name):
    """ML tree with phyml"""

    from Bio.Phylo.Applications import PhymlCommandline
    AlignIO.write(aln, '%s.phy' %name, 'phylip-relaxed')
    cmdline = PhymlCommandline(input='%s.phy' %name, datatype='nt', alpha='e', bootstrap=100)
    print (cmdline)
    cmdline()
    mtree = Phylo.read('%s.phy_phyml_tree.txt' %name,'newick')
    return mtree

def show_alignment(aln, chunks=0, diff=False, offset=0):
    """
    Show a sequence alignment
        Args:
            aln: alignment
            chunks: length of chunks to break lines over, 0 means full length
            diff: whether to show differences
    """

    ref = aln[0]
    l = len(aln[0])
    n=60
    s=[]
    if chunks > 0:
        chunks = [(i,i+n) for i in range(0, l, n)]
    else:
        chunks = [(0,l)]
    for c in chunks:
        start,end = c
        lbls = np.arange(start+1,end+1,10)-offset
        head = ''.join([('%-10s' %i) for i in lbls])
        s.append( '%-21s %s' %('',head) )
        s.append( '%21s %s' %(ref.id[:20], ref.seq[start:end]) )
        if diff == True:
            for a in aln[1:]:
                diff=''
                for i,j in zip(ref,a):
                    if i != j:
                        diff+=j
                    else:
                        diff+='-'
                name = a.id[:20]
                s.append( '%21s %s' %(name, diff[start:end]) )
        else:
            for a in aln[1:]:
                name = a.id[:20]
                s.append( '%21s %s' %(name, a.seq[start:end]) )
    s = '\n'.join(s)
    return s

def get_sequence_colors(seqs, palette='tab20'):
    """Get colors for a sequence"""

    from Bio.PDB.Polypeptide import aa1
    aa1 = list(aa1)
    aa1.append('-')
    aa1.append('X')
    import matplotlib as mpl
    from matplotlib import cm
    pal = cm.get_cmap(palette, 256)
    pal = [mpl.colors.to_hex(i) for i in pal(np.linspace(0, 1, 20))]
    pal.append('white')
    pal.append('white')

    pcolors = {i:j for i,j in zip(aa1,pal)}
    text = [i for s in list(seqs) for i in s]
    clrs =  {'A':'red','T':'green','G':'orange','C':'blue','-':'white'}
    try:
        colors = [clrs[i] for i in text]
    except:
        colors = [pcolors[i] for i in text]
    return colors

def get_protein_colors(palette='tab20'):
    """Get protein color dict"""

    from Bio.PDB.Polypeptide import aa1
    aa1 = list(aa1)
    aa1.append('-')
    aa1.append('X')
    import matplotlib as mpl
    from matplotlib import cm
    pal = cm.get_cmap(palette, 256)
    pal = [mpl.colors.to_hex(i) for i in pal(np.linspace(0, 1, 20))]
    pal.append('white')
    pal.append('white')
    pcolors = {i:j for i,j in zip(aa1,pal)}
    return pcolors

def read_hmmer3(infile):
    """read hmmer3 tab file and return dataframe"""

    def descr_info(x):
        s = re.split('~~~',x)
        return pd.Series(s)
    from Bio import SearchIO
    p = SearchIO.parse(infile, 'hmmer3-tab')
    res=[]
    for qr in p:
        hit= qr.hits[0]
        res.append([qr.id, hit.id, hit.bitscore,hit.evalue,hit.description])
    cols = ['name','query','score','evalue','description']
    df = pd.DataFrame(res,columns=cols)
    if len(df) == 0:
        return
    df[['EC','gene','product']] = df.description.apply(lambda x: descr_info(x))
    df = df.drop(columns=['description'])
    df = df.drop_duplicates('query')
    df['feat_type'] = 'CDS'
    return df

def read_aragorn(infile):
    """Read aragorn file.
    see https://github.com/jorvis/biocode/blob/master/gff/merge_predicted_gff3.py
    """

    res=[]
    for line in open(infile):
        line = line.rstrip()

        if line.startswith('>'):
            m = re.match('>(\S+)', line)
            contig = m.group(1)
        else:
            cols = line.split()

            if len(cols) == 5:
                if cols[1].startswith('tRNA'):
                    feat_type = 'tRNA'
                elif cols[1].startswith('tmRNA'):
                    feat_type = 'tmRNA'
                elif cols[1].startswith('mtRNA'):
                    feat_type = 'mtRNA'
                else:
                    raise Exception("Unexpected type in ARAGORN, column value: {0}".format(cols[1]))

                #feat_base = "{0}_{1}".format(feat_type, uuid.uuid4())
                #gene_id = "{0}_gene".format(feat_base)
                #RNA_id = "{0}_{1}".format(feat_base, feat_type)
                name = cols[1]
                anticodon = cols[4][1:4].upper()
                #print (cols)
                m = re.match('(c*)\[(\d+),(\d+)\]', cols[2])
                if m:
                    start = int(m.group(2)) - 1
                    end = int(m.group(3))
                if m.group(1):
                    rstrand = -1
                else:
                    rstrand = 1
                res.append([contig, name, feat_type, start, end, anticodon, rstrand])

    res = pd.DataFrame(res, columns=['contig', 'product', 'feat_type', 'start', 'end', 'anticodon', 'strand'])
    return res
