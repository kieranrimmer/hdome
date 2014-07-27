import os
import sys
import datetime
from django.utils.timezone import utc
from django.db.models import *
import time
from django.db import connection

PROJ_NAME = 'hdome'
APP_NAME = 'pepsite'

CURDIR = os.path.dirname( os.path.abspath( __file__ ) )

#print CURDIR

sys.path.append( CURDIR + '/../..' ) # gotta hit settings.py for site

os.environ[ 'DJANGO_SETTINGS_MODULE' ] = '%s.settings' %( PROJ_NAME )

import django #required
django.setup() #required

from django.contrib.auth.models import User
from pepsite.models import *
from pepsite import dbtools
import pepsite.uploaders

class QueryOpt( object ):

    def simple_expt_query(self, exp_id, user_id, perm = False):
        """docstring for simple_expt_query"""
        t0 = time.time()
        user = User.objects.get( id = user_id )
        p1 = Peptide.objects.filter(idestimate__ion__experiment = exp_id, idestimate__ion__dataset__confidence_cutoff__lte = F('idestimate__confidence')).distinct()
        v1 = IdEstimate.objects.filter(ion__experiment = exp_id, ion__dataset__confidence_cutoff__lte = F('confidence')).extra( select = {'dm' : "abs(delta_mass)"}).annotate( ptmc = Count('ptms__id') ).distinct()
        if perm:
            dsets = Dataset.objects.filter( experiment__id = exp_id ).distinct()
            for ds in Experiment.objects.get( id = exp_id ).dataset_set.all():
                if not user.has_perm( 'view_dataset', ds ):
                    dsets = dsets.exclude( ds )
            p1 = p1.filter( idestimate__ion__dataset__in = dsets ).distinct()
            v1 = v1.filter( ion__dataset__in = dsets ).distinct()

        #lv1 = len(v1)
        #lp1 = len(p1)
        #print lv1, lp1
        i = 0
        j = 0
        for pep in p1:
            i += 1
            #print 'peptide %d of %d:' % ( i, lp1 )
            v2 = IdEstimate.objects.filter(ion__experiment = exp_id, peptide = pep, ion__dataset__confidence_cutoff__lte = F('confidence')).extra( select = {'dm' : "abs(delta_mass)"}).annotate( ptmc = Count('ptms__id') ).distinct()
            ptmz = []
            for ide in v2:
                ptmcon = [ b.id for b in ide.ptms.all().order_by( 'id' ) ]
                if ptmcon not in ptmz:
                    ptmz.append( ptmcon )
            #ptms = Ptm.objects.filter(idestimate__peptide = pep, idestimate__ion__experiment = expno, idestimate__ion__dataset__confidence_cutoff__lte = F('idestimate__confidence') ).distinct()
            #thruz = IdEstimate.ptms.through.objects.filter( idestimate__ion__experiment = expno, idestimate__in = v2 ).distinct()
            k = 0
            for ptmcon in ptmz:
                a = v2
                if not ptmcon:
                    a = a.filter( ptms__isnull = True, ptmc = 0 ).distinct().order_by( 'dm' )[0]
                    k += 1
                else:
                    a = a.filter( ptmc = len(ptmcon) ).distinct()
                    for ptm in ptmcon:
                       a = v2.filter( ptms = ptm )
                    a = a.distinct().order_by( 'dm' )[0]
                    k += 1
                j += k
                #v2 = v2.filter( ptms = ptm )
            v2 = v2.distinct().annotate( best_dm = Min( 'delta_mass' ) ).filter( best_dm = F('delta_mass') ).distinct()
            #print '%d outputs' % k
        t1 = time.time()
        return (t1 - t0, j, exp_id, user_id, perm)
        print 'f timing:', t1-t0,  ', outputs:', j

    def mkii_expt_query(self, exp_id, user_id, perm = False):
        """docstring for simple_expt_query"""
        expt = Experiment.objects.get( id = exp_id )
        print expt.title
        t0 = time.time()
        user = User.objects.get( id = user_id )
        dsets = Dataset.objects.filter( experiment__id = exp_id ).distinct()
        for ds in Experiment.objects.get( id = exp_id ).dataset_set.all():
            if not user.has_perm( 'view_dataset', ds ):
                dsets = dsets.exclude( ds )
        p1 = Peptide.objects.filter(idestimate__ion__experiment = exp_id, idestimate__ion__dataset__confidence_cutoff__lte = F('idestimate__confidence')).distinct()
        sql1 = "select ptmstr from pepsite_idestimate t3 left outer join (select t1.id, t1.confidence, \
                array_to_string(array_agg(t2.ptm_id order by t2.ptm_id),\'+\') as ptmstr from pepsite_idestimate t1 \
                left outer join pepsite_idestimate_ptms t2 on (t2.idestimate_id = t1.id) group by t1.id) as foo \
                on(foo.id = t3.id) where t3.id = pepsite_idestimate.id"
        v1 = IdEstimate.objects.extra( select = { 'ptmstr' :sql1, 'dm' : "abs(delta_mass)" } ).\
                filter( ion__experiment = exp_id, ion__dataset__confidence_cutoff__lte = F('confidence'), ion__dataset__in = dsets )\
                .order_by( 'dm' ).values( 'ptmstr', 'peptide', 'id' ).annotate( ptmc = Count('ptms') ).distinct().order_by('-ptmc')\
                
        j = v1.count()
        t1 = time.time()
        return (v1, t1 - t0, j, exp_id, user_id, perm)

    def mkiii_expt_query(self, exp_id, user_id, perm = False):
        """docstring for simple_expt_query"""
        t0 = time.time()
        cursor = connection.cursor()
        cursor.execute( "DROP VIEW IF EXISTS \"allowedides\"" )
        cursor.execute( "DROP VIEW IF EXISTS \"suppavail\" CASCADE" )
        cursor.execute( "DROP VIEW IF EXISTS \"suppcorrect\"" )
        cursor.execute( "DROP VIEW IF EXISTS \"sv2\"" )
        expt = Experiment.objects.get( id = exp_id )
        print expt.title
        user = User.objects.get( id = user_id )
        dsets = Dataset.objects.filter( experiment__id = exp_id ).distinct()
        for ds in Experiment.objects.get( id = exp_id ).dataset_set.all():
            if not user.has_perm( 'view_dataset', ds ):
                dsets = dsets.exclude( ds )
        qq1 = IdEstimate.objects.filter( ion__dataset__in = dsets, ion__dataset__confidence_cutoff__lte = F('confidence') ).distinct().query
        cursor.execute( 'CREATE VIEW \"allowedides\" AS ' + str( qq1 ) )
        qq2 = "CREATE VIEW suppavail AS SELECT foo.id, foo.ptmstr,\
                min(abs(foo.delta_mass)) FROM (select t1.id, t1.confidence, t1.peptide_id, \
                t1.delta_mass, array_to_string(array_agg(t2.ptm_id order by t2.ptm_id),'+') AS ptmstr FROM \
                pepsite_idestimate t1 LEFT OUTER JOIN pepsite_idestimate_ptms t2 ON (t2.idestimate_id = t1.id) \
                \
                group by t1.id, t1.peptide_id) AS foo \
                GROUP BY foo.id, foo.ptmstr \
                "
        qq2a = "CREATE VIEW sv2 AS SELECT * FROM suppavail WHERE adm = min"
        qq3 = "CREATE VIEW suppcorrect AS SELECT DISTINCT foo.peptide_id, foo.ptmstr, min(abs(foo.delta_mass)) \
                FROM (select t1.id, t1.confidence, t1.peptide_id, t1.delta_mass, \
                array_to_string(array_agg(t2.ptm_id order by t2.ptm_id),'+') AS ptmstr FROM pepsite_idestimate \
                t1 LEFT OUTER JOIN pepsite_idestimate_ptms t2 ON (t2.idestimate_id = t1.id) \
                GROUP BY t1.id) AS \
                foo GROUP BY foo.peptide_id, foo.ptmstr"
        sql1 = "select ptmstr from pepsite_idestimate t3 left outer join (select t1.id, t1.confidence, \
                array_to_string(array_agg(t2.ptm_id order by t2.ptm_id),\'+\') as ptmstr from pepsite_idestimate t1 \
                left outer join pepsite_idestimate_ptms t2 on (t2.idestimate_id = t1.id) group by t1.id) as foo \
                on(foo.id = t3.id) where t3.id = pepsite_idestimate.id"
        qq4 = "SELECT DISTINCT allowedides.id FROM suppcorrect t1 \
                INNER JOIN suppavail t2 ON (t2.min = t1.min AND t2.ptmstr = t1.ptmstr) \
                INNER JOIN allowedides ON (t2.id = allowedides.id AND t1.min = abs(allowedides.delta_mass))"
        qq4a = "SELECT * FROM \
                ( \
                SELECT DISTINCT t1.peptide_id, t1.ptmstr, min(tds.id) as dsmin FROM suppcorrect t1 \
                INNER JOIN suppavail t2 ON (t2.min = t1.min AND t2.ptmstr = t1.ptmstr) \
                INNER JOIN allowedides ON (t2.id = allowedides.id AND t1.min = abs(allowedides.delta_mass)) \
                INNER JOIN pepsite_ion ON (pepsite_ion.id = allowedides.id) \
                INNER JOIN pepsite_dataset tds \
                ON ( pepsite_ion.dataset_id = tds.id ) \
                GROUP BY t1.peptide_id, t1.ptmstr \
                ) AS perm1\
                INNER JOIN suppcorrect t3 ON ( t3.ptmstr = perm1.ptmstr ) \
                "
        qq4a = "SELECT DISTINCT allowedides.id FROM suppcorrect t1 INNER JOIN \
                allowedides ON (t1.peptide_id = allowedides. AND t1.min = abs(allowedides.delta_mass))"
        cursor.execute( qq2 )
        cursor.execute( 'SELECT COUNT(*) FROM suppavail' )
        print cursor.fetchall(  )
        #cursor.execute( 'SELECT COUNT(foo.peptide_id) FROM (SELECT DISTINCT peptide_id, ptmstr FROM suppavail) as foo' )
        #print cursor.fetchall(  )
        #cursor.execute( qq2a )
        #cursor.execute( 'SELECT COUNT(*) FROM sv2' )
        #print cursor.fetchall(  )
        cursor.execute( qq3 )
        cursor.execute( 'SELECT COUNT(*) FROM suppcorrect' )
        print cursor.fetchall(  )
        cursor.execute( qq4 )
        ides = cursor.fetchall()
        j = len(ides)
        cursor.execute( "DROP VIEW IF EXISTS \"allowedides\"" )
        cursor.execute( "DROP VIEW IF EXISTS \"suppavail\" CASCADE" )
        cursor.execute( "DROP VIEW IF EXISTS \"suppcorrect\"" )
        cursor.close()
        #ideobjs = IdEstimate.objects.filter( id__in = [b[0] for b in ides] ).distinct()
        #ideobjs = ideobjs.filter( 
        t1 = time.time()
        return (ides, t1 - t0, j, exp_id, user_id, perm)

    def rapid_array(self, valuz, expt_id):
        """docstring for rapid_array"""
        t0 = time.time()
        expt = Experiment.objects.get( id = expt_id )
        rows = []
        #idlist =  [ b['id'] for b in valuz]
        ides = IdEstimate.objects.filter( id__in = valuz ).distinct()
        for ide in ides:
            for prot in Protein.objects.filter( peptoprot__peptide__idestimate = ide ).distinct():
                p2p = PepToProt.objects.get( peptide = ide.peptide, protein = prot )
                row = { 'ide': ide, 'ptms' : ide.ptms.all(), 'expt' : expt, 'ds' : ide.ion.dataset, 'protein' : prot, 'peptoprot' : p2p } 
                rows.append(row)
        t1 = time.time()
        return (t1 - t0, len(rows) )

    def make_array_from_ide_vals(self, valuz, expt_id):
        """docstring for make_array_from_ides"""
        t0 = time.time()
        rows = []
        expt = Experiment.objects.get( id = expt_id )
        i = 0
        for local in valuz:
            i += 1
            #print i,
            ide = IdEstimate.objects.get( id = local )
            #pep = ide.peptide
            ptms = ide.ptms.all()
            ds = ide.ion.dataset
            proteins = Protein.objects.filter( peptoprot__peptide__idestimate = ide ).distinct()
            #print proteins.count(),
            for prot in proteins:
                p2p = PepToProt.objects.get( peptide = ide.peptide, protein = prot )
                row = { 'ide': ide, 'ptms' : ptms, 'expt' : expt, 'ds' : ds, 'protein' : prot, 'peptoprot' : p2p } 
                rows.append(row)
        t1 = time.time()
        return ( t1 - t0, rows )


if __name__=='__main__':
    exp_id = 1
    user_id = 1
    print 'here we go... expecting 1578 returns...\n'
    qo = QueryOpt()
    q2r = qo.mkii_expt_query( exp_id, user_id, perm = False)
    ar1 = q2r[0]
    print ar1
    print ar1.count()
    #print dir(q1r[0])
    print '\n\nmkii_expt_query ran in %f seconds with %d outputs for expt_id = %d, user_id = %d, permission checking = %r\n\n' %  q2r[1:]   #print 'simple_expt_query ran in %f seconds with %d outputs for expt_id = %d, user_id = %d, permission checking = %r' % qo.simple_expt_query( exp_id, user_id, perm = False)
    q3r = qo.mkiii_expt_query( exp_id, user_id, perm = False)
    print '\n\nmkiii_expt_query ran in %f seconds with %d outputs for expt_id = %d, user_id = %d, permission checking = %r\n\n' %  q3r[1:]   #print 'simple_expt_query ran in %f seconds with %d outputs for expt_id = %d, user_id = %d, permission checking = %r' % qo.simple_expt_query( exp_id, user_id, perm = False)
    print q3r[0][:4]
    ar1 = [b[0] for b in q3r[0]][:]
    #print '\n\nrapid_array ran for %f seconds and returned %d results\n\n' % ( qo.rapid_array(ar1, exp_id)  )
    #q2r = qo.make_array_from_ide_vals( ar1, exp_id )
    #print '\n\nassembled array of size %d in %f seconds\n\n' % ( q2r[1].count(), q2r[0] )
    #print q2r[1][:3]
    #print 'simple_expt_query ran in %f seconds with %d outputs for expt_id = %d, user_id = %d, permission checking = %r' % qo.simple_expt_query( exp_id, user_id, perm = True)

    #i = 0
    #for ide in v1:
    #    i += 1
    #    print '%d of %d:' % ( i, lv1 )
    #    v2 = IdEstimate.objects.filter(ion__experiment = 2, peptide = ide.peptide, ion__dataset__confidence_cutoff__lte = F('confidence')).annotate( ptmc = Count('ptms__id') ).filter( ptmc = len( ide.ptms.all() )).distinct()
    #    ptms = ide.ptms.all()
    #    for ptm in ptms:
    #        v2 = v2.filter( ptms = ptm )
    #    v2 = v2.distinct().annotate( best_dm = Min( 'delta_mass' ) ).filter( best_dm = F('delta_mass') ).distinct()
    #    print '%d outputs' % len(v2)

