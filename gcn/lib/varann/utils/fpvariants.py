#
# COPYRIGHT (C) 2012-2013 TCS Ltd
#
"""
.. module:: fpvariants
    :platform: Unix, Windows, MacOSX
    :synopsis: Module to list out variants downstream to frameshift/stopgain
               mutation also present in same chromatid.

.. moduleauthor:: Kunal Kundu (kunal@atc.tcs.com); modified by changjin.hong@gmail.com

Module to list out variants downstream to frameshift/stopgain mutation also
present in same chromatid.

INPUT -
Input to this module -
    i.   VCF file
    ii.  Child SampleID in VCF
    iii. Father SampleID in VCF
    iv.  Mother SampleID in VCF
    v.   Threshold GQ (Genotype Quality)
This module also works if the parent information is not known.

OUTPUT -
The output is in tsv format and is printed to console.
"""

from gcn.lib.io import vcf
import sys
import argparse
from gcn.lib.databases.refgene import Refgene
from gcn.lib.utils.phase import phase
from gcn.lib.varann.vartype.varant import varant_parser as vp


def check_genotype(rec, pedigree, GQ_THRES):
    """Checks for presence of genotype and its quality
    for the Child SampleID, Father SampleID and Mother
    SampleID.
    Args:
        - rec(dictionary):    Parsed vcf record as generated by VCF parser.
        - pedigree(list):    [Father SampleID, Mother SampleID,
                              Child SampleID]. Expects the order in which
                              the SampleIDs are mentioned above.
        - GQ_THRES(int):    Threshold Genotype Quality

    Returns:
        - genotypes(tuple):    Genotypes of the pedigree.
                               For e.g. genotypes=('0/1', '0/0', '0/1')
                               Genotypes are in order
                               - Father, Mother, Child in the tuple.
    """
    genotypes = []
    c = pedigree[2]  # Child
    if rec[c]['GT'] != './.' and rec[c]['GQ'] >= GQ_THRES:
        if rec[c]['GT'] != '0/0':
            genotypes.append(rec[c]['GT'])

            if pedigree[0]:  # Father
                p1 = pedigree[0]
                if rec[p1]['GT'] != './.' and rec[p1]['GQ'] >= GQ_THRES:
                    genotypes.insert(0, rec[p1]['GT'])
                else:
                    genotypes.insert(0, './.')
            else:
                genotypes.insert(0, './.')

            if pedigree[1]:  # Mother
                p2 = pedigree[1]
                if rec[p2]['GT'] != './.' and rec[p2]['GQ'] >= GQ_THRES:
                    genotypes.insert(1, rec[p2]['GT'])
                else:
                    genotypes.insert(1, './.')
            else:
                genotypes.insert(1, './.')
        else:
            return genotypes
    else:
        return genotypes
    return tuple(genotypes)


def get_gene_data(vcffile, pedigree, GQ_THRES):
    """Retrieves gene_transcript wise variants where there exits at least one
    frameshift/stopgain mutation.
    Args:
        - vcffile(str):    Input VCF file.
                           Note - VCF should be VARANT annotated.
        - pedigree(list):    [Father SampleID, Mother SampleID,
                        Child SampleID]. Expects the order in which
                        the SampleIDs are mentioned above.
        - GQ_THRES(int):    Threshold Genotype Quality

    Returns:
        - gene_data_phased(dictionary):    Genotype Phased gene_transcript
                                           wise variants where there is
                                           at least one Frameshift/
                                           Stopgain mutation.
        - gene_data_unphased(dictionary):    Genotype Unphased gene_transcript
                                             wise variants where there is
                                             at least one Frameshift/Stopgain
                                             mutation in homozygous state.
    """
    data1 = {}
    data2 = {}
    FILTER = ['PASS', 'VQSRTrancheSNP99.00to99.90']
    v = vcf.VCFParser(vcffile)
    for rec in v:
        v.parseinfo(rec)
        v.parsegenotypes(rec)
        varfltr = rec['filter']
        if len([True for flt in FILTER if flt in varfltr]) > 0:
            genotypes = check_genotype(rec, pedigree, GQ_THRES)
            if genotypes:
                pg = phase(*genotypes)
                if pg[1] == '|':
                    c1, c2 = int(pg[0]), int(pg[-1])
                    va = vp.parse(rec.info)
                    for idx, altid in enumerate([c1, c2]):
                        if altid != 0:
                            if altid in va:
                                gene = va[altid].keys()[0]
                                if len(va[altid][gene]) > 0:
                                    for ta in va[altid][gene]['TRANSCRIPTS']:
                                        if ta.region == 'CodingExonic':
                                            trans_id = ta.trans_id
                                            key = (rec.chrom, rec.pos, \
                                                   ','.join(rec.id), rec.ref, \
                                                   rec.alt[altid - 1], altid)
                                            gi = (gene, trans_id)
                                            if gi not in data1:
                                                data1[gi] = [{}, {}]
                                                data1[gi][idx][key] = \
                                                                [ta.mutation,
                                                                 pg,
                                                                 genotypes[0],
                                                                 genotypes[1]]
                                            else:
                                                data1[gi][idx][key] = \
                                                                [ta.mutation,
                                                                 pg,
                                                                 genotypes[0],
                                                                 genotypes[1]]
                else:
                    c1, c2 = int(pg[0]), int(pg[-1])
                    va = vp.parse(rec.info)
                    for altid in [c1, c2]:
                        if altid != 0:
                            if altid in va:
                                gene = va[altid].keys()[0]
                                if len(va[altid][gene]) > 0:
                                    for ta in va[altid][gene]['TRANSCRIPTS']:
                                        if ta.region == 'CodingExonic':
                                            trans_id = ta.trans_id
                                            key = (rec.chrom, rec.pos, \
                                                ','.join(rec.id), rec.ref, \
                                                   rec.alt[altid - 1], altid)
                                            gi = (gene, trans_id)
                                            if gi not in data2:
                                                data2[gi] = [{}]
                                                data2[gi][0][key] = \
                                                            [ta.mutation,
                                                             pg,
                                                             genotypes[0],
                                                             genotypes[1]]
                                            else:
                                                data2[gi][0][key] = \
                                                            [ta.mutation,
                                                             pg,
                                                             genotypes[0],
                                                             genotypes[1]]
    gene_data_phased = {}
    for k, v in data1.items():
        for e in v:
            if len(e) > 0:
                if len(e.values()) > 1:
                    if len([True for mut in [x[0] for x in e.values()] \
                            if mut.startswith('FrameShift') \
                            or mut == 'StopGain']) > 0:
                        if k not in gene_data_phased:
                            gene_data_phased[k] = [e]
                        else:
                            gene_data_phased[k].append(e)
    del data1
    gene_data_unphased = {}
    for k, v in data2.items():
        for e in v:
            if len(e) > 0:
                if len(e.values()) > 1:
                    if len([True for y in [(x[0], x[1]) for x in e.values()] \
                             if (y[0].startswith('FrameShift') or \
                                 y[0] == 'StopGain') and \
                                 int(y[1][0]) == int(y[1][2])]) > 0:
                        if k not in gene_data_unphased:
                            gene_data_unphased[k] = [e]
                        else:
                            gene_data_unphased[k].append(e)
    del data2
    return gene_data_phased, gene_data_unphased


def filter_dwnmut(gene_data):
    """Removes the variants upstream to Frameshift/StopGain mutation.
    Args:
        - gene_data(dictionary):     gene_transcript wise variants where
                                     there is at least one Frameshift/Stopgain
                                     mutation.

    Returns:
        - flt_data(dictionary):    gene_transcript wise variants where there
                                   is at least one Frameshift/StopGain mutation
                                   and at least one downstream coding exonic
                                   variant.
    """
    rfgene = Refgene()
    flt_gene_data = {}
    for gene_info, val in gene_data.items():
        trans_id = gene_info[1]
        strand = rfgene.get_strand(trans_id)
        if not strand:
            continue
        for e in val:
            t = {}
            variants = e.keys()
            if strand == '+':
                variants.sort()
            elif strand == '-':
                variants.sort(reverse=True)
            size = 0
            mut_type = ''
            flag = False

            for var in variants:
                if flag == False and e[var][0] == 'StopGain':
                    mut_type = 'StopGain'
                    t[tuple(list(var) + ['#'])] = e[var]
                    flag = True

                elif flag == False and e[var][0].startswith('FrameShift'):
                    if e[var][0][10:] == 'Insert':
                        size += len(var[4]) - 1
                    elif e[var][0][10:] == 'Delete':
                        size -= len(var[3]) - 1
                    t[tuple(list(var) + ['#'])] = e[var]
                    flag = True

                elif flag == True:
                    if mut_type == 'StopGain':
                        t[var] = e[var]
                    elif e[var][0].startswith('FrameShift'):
                        if e[var][0][10:] == 'Insert':
                            size += len(var[4]) - 1
                        elif e[var][0][10:] == 'Delete':
                            size -= len(var[3]) - 1
                        t[var] = e[var]
                        if size == 0 or divmod(size, 3)[1] == 0:
                            flag = False
                    elif e[var][0].startswith('NonFrameShift'):
                        if e[var][0][13:] == 'Insert':
                            size += len(var[4]) - 1
                        elif e[var][0][13:] == 'Delete':
                            size -= len(var[3]) - 1
                        t[var] = e[var]
                        if size == 0 or divmod(size, 3)[1] == 0:
                            flag = False
                    else:
                        t[var] = e[var]

            if len(t) > 1:
                key = tuple(list(gene_info) + [strand])
                if key not in flt_gene_data:
                    flt_gene_data[key] = [t]
                else:
                    if t != flt_gene_data[key][0]:
                        flt_gene_data[key].append(t)
    return flt_gene_data


def display(d1, d2, pedigree, vcffile):
    """Prints to console the Coding Exonic variants downstream to
    Frameshift/StopGain Mutation."""
    print '## VCF file used %s' % vcffile
    print '## Pedigree used %s' % ','.join([e for e in pedigree if e])
    print '## Details about list of variants downstream to \
              FrameShift/StopGain Mutation.'
    header = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'ALT_ID', 'GENE',
              'TRANSCRIPT', 'STRAND', 'MUTATION', 'TYPE', 'CHROMATID',
              'CHILD-%s' % pedigree[-1]]
    if pedigree[0]:
        header.append('FATHER-%s' % pedigree[0])
    if pedigree[1]:
        header.append('MOTHER-%s' % pedigree[1])
    print '\t'.join(header)
    for d in [d1, d2]:
        gene_info = d.keys()
        gene_info.sort()
        for gi in gene_info:
            gene, trans_id, strand = gi
            val = d[gi]
            chrom_pair = 0
            for e in val:
                chrom_pair += 1
                variants = e.keys()
                if strand == '+':
                    variants.sort()
                else:
                    variants.sort(reverse=True)
                for variant in variants:

                    if int(e[variant][1][0]) == int(e[variant][1][-1]):
                        chromatid = 'BOTH_CHROM'
                    elif e[variant][1][1] == '|':
                        if variant[5] == int(e[variant][1][0]):
                            chromatid = 'FATHER_CHROM'
                        elif variant[5] == int(e[variant][1][-1]):
                            chromatid = 'MOTHER_CHROM'
                    else:
                        chromatid = 'UNKNOWN_CHROM'
                    if variant[-1] == '#':
                        print '\n'
                        print '\t'.join([str(x) for x in variant[:-1]] + \
                                        [gene, trans_id, strand,
                                         e[variant][0],
                                         e[variant][0].upper(),
                                         chromatid] + e[variant][1:])
                    else:
                        print '\t'.join([str(x) for x in variant] + \
                                        [gene, trans_id, strand,
                                         e[variant][0], 'DOWNSTREAM',
                                         chromatid] + e[variant][1:])


def compute(vcffile, GQ_THRES, pedigree):
    """Identifies the coding exonic variants downstream to frameshift/
    stopgain mutation and prints the output to console."""

    # Get the coding exonic variants transcript wise where for a transcript
    # there is atleast one frameshift/stopgain causing variant.
    gene_data_phased, gene_data_unphased = get_gene_data(vcffile,
                                                         pedigree, GQ_THRES)

    # Remove the variants upstream to Frameshift/stopgain causing variant
    # for phased data
    dwnmut_data_phased = filter_dwnmut(gene_data_phased)

    # Remove the variants upstream to Frameshift/stopgain causing variant
    # for unphased data
    dwnmut_data_unphased = filter_dwnmut(gene_data_unphased)

    # Print the output to console
    display(dwnmut_data_phased, dwnmut_data_unphased, pedigree, vcffile)


def main():
    """Main script to extract exoding exonic variants downstream to Frameshift/
       StopGain mutation and also present in same chromatid."""
    desc = 'Script to extract all CodingExonic variants downstream to\
            FrameShift mutation and also occuring in same chromatid.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-i', '--input', dest='vcffile', type=str,
                        help='VCF file')
    parser.add_argument('-f', '--father', dest='father', type=str,
                        help='Sample Name for Father as mentioned in VCF')
    parser.add_argument('-m', '--mother', dest='mother', type=str,
                        help='Sample Name for Mother as mentioned in VCF')
    parser.add_argument('-c', '--child', dest='child', type=str,
                        help='Sample Name for Child as mentioned in VCF')
    parser.add_argument('-GQ', '--genotype_quality', dest='gq', type=str,
                        default=30, help='Genotype Quality of the Samples')
    args = parser.parse_args()
    pedigree = [args.father, args.mother, args.child]
    compute(args.vcffile, float(args.gq), pedigree)
    sys.exit(0)

if __name__ == '__main__':
    main()
