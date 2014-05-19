from django.db import models
from django.contrib.auth.models import User
import datetime
from django.utils.timezone import utc


NOW = models.DateTimeField( default = datetime.datetime.utcnow().replace(tzinfo=utc) )


def fname():
    """docstring for fname"""
    pass

def yello():
	"""docstring for yello"""
	pass

class Gene(models.Model):
    name = models.CharField(max_length=200)
    gene_class = models.IntegerField()
    description = models.TextField( default = '' )

    def __str__(self):
	return self.name + '|Class-' + str(self.gene_class)

class Allele(models.Model):
    gene = models.ForeignKey( Gene )
    code = models.CharField(max_length=200)
    #dna_type = models.CharField(max_length=200)
    #ser_type = models.CharField(max_length=200)
    isSer = models.BooleanField( default = False )
    description = models.TextField( default = '' )

    def get_summary( self ):
	pass

    def get_class( self ):
	return self.__class__

    def __str__(self):
	return self.code

    class Meta:
    	unique_together = ( ('gene', 'code'), )

    def get_experiments( self ):
	return Experiment.objects.filter( cell_line__alleles = self, antibody__alleles = self  ).distinct()



class Entity(models.Model):
    common_name = models.CharField(max_length=200)
    sci_name = models.CharField(max_length=200 )
    description = models.TextField( default = '' )
    isOrganism = models.BooleanField( default = False )

    def __str__(self):
	return self.common_name

    def find_cell_lines( self ):
	return CellLine.objects.filter( individuals__entity = self ).distinct()


class Individual(models.Model):
    identifier = models.CharField(max_length=200, unique = True )
    description = models.TextField( default = '' )
    nation_origin = models.CharField(max_length=200 )
    entity = models.ForeignKey( Entity, blank=True, null=True )
    isHost = models.BooleanField( default = False )
    isAnonymous = models.BooleanField( default = True )
    web_ref = models.CharField(max_length=200 )




    def __str__(self):
	return self.identifier

class CellLine(models.Model):
    name = models.CharField(max_length=200)
    tissue_type = models.CharField(max_length=200)
    isTissue = models.BooleanField(default=False)
    description = models.TextField( default = '' )
    #host = models.ForeignKey( Organism, related_name = 'HostCell' )
    #infecteds = models.ManyToManyField( Organism, related_name = 'Infections' )
    individuals = models.ManyToManyField( Individual )
    alleles = models.ManyToManyField( Allele, through='Expression' )
    #antibodies = models.ManyToManyField( Antibody )

    class Meta:
        """docstring for Meta"""
        unique_together = ('name', 'description')
            

    def __str__(self):
	return self.name

    def get_antibodies_targeting( self ):
	return Antibody.objects.filter( alleles__cellline = self, experiments__cell_line = self ).distinct()

    def get_organisms( self ):
	return Entity.objects.filter( isOrganism = True, individual__cellline = self )


class Expression(models.Model):
    """docstring for Expression"""
    cell_line = models.ForeignKey( CellLine )
    allele = models.ForeignKey( Allele )
    isSilenced = models.BooleanField( default = False )
    expression_level = models.FloatField( default = 100.0 )

    def __str__(self):
        """docstring for __str__"""
        return self.cell_line.name + '|' + self.allele.code
        

class Lodgement(models.Model):
    """docstring for Lodgement"""
    datetime = models.DateTimeField( )
    title = models.CharField( max_length = 300 )
    user = models.ForeignKey(User)
    isFree = models.BooleanField( default = False )

    def __str__(self):
        return self.datetime.strftime("%Y-%m-%d %H:%M:%S")

class Experiment( models.Model ):
    title = models.CharField(max_length=200)
    description = models.TextField( default = '' )
    #date_time = models.DateTimeField('date run')
    #data = models.FileField()
    cell_line = models.ForeignKey( CellLine )
    #lodgement = models.ForeignKey( Lodgement )

    def __str__(self):
	return self.title

    def get_common_alleles( self ):
	return Allele.objects.filter( antibody__experiments = self, cellline__experiment = self )

class Antibody(models.Model):
    name = models.CharField(max_length=200, unique = True )
    description = models.TextField( default = '' )
    alleles = models.ManyToManyField( Allele )
    experiments = models.ManyToManyField( Experiment )

    def __str__(self):
	return self.name

    def get_cell_lines_targeted( self ):
	return CellLine.objects.filter( alleles__antibody = self, experiment__antibody = self ).distinct()

class Ptm(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField( default = '' )
    mass_change = models.FloatField()

    def fname(self):
        """docstring for fname"""
        pass

    def __str__(self):
	return self.description + '|' + str( self.mass_change )


class Protein(models.Model):
    #prot_id = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.TextField( default = '' )
    sequence = models.TextField( default = '' )

    def __str__(self):
	return self.prot_id + '|' + self.name

class Peptide(models.Model):
    sequence = models.CharField(max_length=200)
    mass = models.FloatField()
    proteins = models.ManyToManyField( Protein, through='PepToProt' )
    #ptms = models.ManyToManyField( Ptm )

    def __str__(self):
	return self.sequence


class Position(models.Model):
    """docstring for Position"""
    initial_res = models.IntegerField()
    final_res = models.IntegerField()

    def __str__(self):
        """docstring for __str__"""
        return "%d-%d" %( self.initial_res, self.final_res )
        

class PepToProt(models.Model):
    """docstring for PepToProt"""
    peptide = models.ForeignKey(Peptide)
    protein = models.ForeignKey(Protein)
    positions = models.ManyToManyField(Position)

    def __str__(self):
        """docstring for __str__"""
        return self.peptide.sequence + '--' + self.protein.name


class Ion(models.Model):
    precursor_mass = models.FloatField()
    charge_state = models.IntegerField()
    retention_time = models.FloatField()
    experiments = models.ManyToManyField(Experiment)
    peptides = models.ManyToManyField( Peptide, through='IdEstimate')
    #antibodies = models.ManyToManyField( Antibody )
    #cell_lines = models.ManyToManyField( CellLine )

    def __str__(self):
	return str(self.precursor_mass) + '|' + str(self.charge_state)


class IdEstimate(models.Model):
    peptide = models.ForeignKey(Peptide)
    ion = models.ForeignKey(Ion)
    ptm = models.ForeignKey(Ptm, null = True)
    #experiment = models.ForeignKey(Experiment)
    delta_mass = models.FloatField()
    confidence = models.FloatField()

    def check_ptm(self):
        """docstring for check_ptm"""
        if not self.ptm or self.ptm.description in ( '', ' ',
                '[undefined]', '[undefined] ' ):
            return False
        else:
            return True

    def __str__(self):
	return str(self.delta_mass) + '|' + str(self.confidence)

class Manufacturer(models.Model):
    """docstring for Manufacturer"""
    name = models.CharField(max_length=200)

    def __str__(self):
        """docstring for __str__"""
        return self.name
        

class Instrument(models.Model):
    """docstring for Instrument"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    manufacturer = models.ForeignKey(Manufacturer)

    def __str__(self):
        """docstring for __str__"""
        return self.name
        

class Dataset(models.Model):
    """docstring for Dataset"""
    title = models.CharField(max_length=300)
    datetime = models.DateTimeField( )
    data = models.FileField()
    gradient_min = models.FloatField()
    gradient_max = models.FloatField()
    gradient_duration = models.FloatField()
    instrument = models.ForeignKey(Instrument)
    lodgement = models.ForeignKey(Lodgement)
    ions = models.ManyToManyField( Ion )

    def __str__(self):
        """docstring for __str__"""
        return self.title 

        

class ExternalDb(models.Model):
    """docstring for ExternalDb"""
    db_name = models.CharField(max_length=200)
    url_stump = models.CharField(max_length=400)
    url_suffix = models.CharField(max_length=400)

    def __str__(self):
        """docstring for __str__"""
        return self.db_name + '|' + self.url_stump
        

class LookupCode(models.Model):
    """docstring for Code"""
    code = models.CharField(max_length=200)
    externaldb = models.ForeignKey( ExternalDb )
    protein = models.ForeignKey( Protein, null=True )
    cell_lines = models.ManyToManyField( CellLine )

    def __str__(self):
        """docstring for __str__"""
        return self.code


class Publication(models.Model):
    """docstring for Publication"""
    title = models.TextField()
    journal = models.TextField()
    display = models.TextField()
    lodgements = models.ManyToManyField( Lodgement )
    cell_lines = models.ManyToManyField( CellLine )
    lookupcode = models.OneToOneField( LookupCode )

    def __str__(self):
        """docstring for _"""
        return self.title + '|' + self.journal

        





