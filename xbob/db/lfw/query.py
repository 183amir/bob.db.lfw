#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# @author: Manuel Guenther <Manuel.Guenther@idiap.ch> 
# @date: Thu May 24 10:41:42 CEST 2012
#
# Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""This module provides the Dataset interface allowing the user to query the
LFW database.
"""

from bob.db import utils
from .models import *
from sqlalchemy.orm import aliased
from .driver import Interface

INFO = Interface()

SQLITE_FILE = INFO.files()[0]

class Database(object):
  """The dataset class opens and maintains a connection opened to the Database.

  It provides many different ways to probe for the characteristics of the data
  and for the data itself inside the database.
  """

  def __init__(self):
    # opens a session to the database - keep it open until the end
    self.connect()
    self.m_valid_protocols = ('view1', 'fold1', 'fold2', 'fold3', 'fold4', 'fold5', 'fold6', 'fold7', 'fold8', 'fold9', 'fold10')
    self.m_valid_groups = ('world', 'dev', 'eval')
    self.m_valid_purposes = ('enrol', 'probe')
    self.m_valid_classes = ('matched', 'unmatched')
    self.m_valid_subworlds = ('onefolds', 'twofolds', 'threefolds', 'fourfolds', 'fivefolds', 'sixfolds', 'sevenfolds')
    self.m_subworld_counts = {'onefolds':1, 'twofolds':2, 'threefolds':3, 'fourfolds':4, 'fivefolds':5, 'sixfolds':6, 'sevenfolds':7}
    self.m_valid_types = ('restricted', 'unrestricted')
 
  def connect(self):
    """Tries connecting or re-connecting to the database"""
    if not os.path.exists(SQLITE_FILE):
      self.m_session = None

    else:
      self.m_session = utils.session(INFO.type(), INFO.files()[0])

  def is_valid(self):
    """Returns if a valid session has been opened for reading the database"""

    return self.m_session is not None

  def __check_single__(self, value, description, valid):
    if not isinstance(value, str):
      raise ValueError("The given %s has to be of type 'str'" % description)
    if not value in valid:
      raise ValueError("The given %s '%s' need to be one of %s" %(description, value, valid) )

  def __check_validity__(self, list, description, valid):
    """Checks validity of user input data against a set of valid values"""
    if not list: return valid
    elif isinstance(list, str): return self.__check_validity__((list,), description, valid)
    for k in list:
      if k not in valid:
        raise RuntimeError, 'Invalid %s "%s". Valid values are %s, or lists/tuples of those' % (description, k, valid)
    return list
  
  def __eval__(self, fold):
    return int(fold[4:])

  def __dev__(self, eval):
    # take the two parts of the training set (the ones before the eval set) for dev 
    return ((eval + 7) % 10 + 1, (eval + 8) % 10 + 1)
    
  def __dev_for__(self, fold):
    return ["fold%d"%f for f in self.__dev__(self.__eval__(fold))]
  
  def __world_for__(self, fold, subworld):
    # the training sets for each fold are composed of all folds
    # except the given one and the previous
    eval = self.__eval__(fold)
    dev = self.__dev__(eval)
    world_count = self.m_subworld_counts[subworld]
    world = []
    for i in range(world_count):
      world.append((eval + i) % 10 + 1) 
    return ["fold%d"%f for f in world]
  
  def __make_path__(self, stem, directory, extension):
    import os
    if not extension: extension = ''
    if directory: return os.path.join(directory, stem + extension)
    return stem + extension


  def clients(self, protocol=None, groups=None, subworld='sevenfolds'):
    """Returns a set of clients for the specific query by the user.

    Keyword Parameters:

    protocol
      The protocol to consider; one of: ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the clients belong; one or several of: ('world', 'dev', 'eval')
      The 'eval' group does not exist for protocol 'view1'.
      
    subworld
      The subset of the training data. Has to be specified if groups includes 'world' 
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').
      
    Returns: A list containing all client names which have the desired properties.
    """

    self.__check_single__(protocol, 'protocol', self.m_valid_protocols)
    groups = self.__check_validity__(groups, 'group', self.m_valid_groups)
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_valid_subworlds)
 
    queries = []
 
    # List of the clients
    if protocol == 'view1':
      if 'world' in groups:
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.m_protocol == 'train').\
                  order_by(Client.m_name))
      if 'dev' in groups:
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.m_protocol == 'test').\
                  order_by(Client.m_name))
    else:
      if 'world' in groups:
        # select training set for the given fold
        trainset = self.__world_for__(protocol, subworld)
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.m_protocol.in_(trainset)).\
                  order_by(Client.m_name))
      if 'dev' in groups:
        # select development set for the given fold
        devset = self.__dev_for__(protocol)
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.m_protocol.in_(devset)).\
                  order_by(Client.m_name))
      if 'eval' in groups:
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.m_protocol == protocol).\
                  order_by(Client.m_name))
        
    # all queries are made; now collect the names
    retval = []
    for query in queries: 
      for k in query:
        retval.append(k.m_name)
        
    # assure that the list of names is unique
    assert len(set(retval)) == len(retval)
    return retval


  def models(self, protocol=None, groups=None, subworld='sevenfolds', type='restricted'):
    """Returns a set of models (multiple models per client) for the specific query by the user.
    Note that for 'world' sets in the 'restricted' case, both images of the pairs are returned,
    while for the 'dev' and 'eval' groups, only the first element of the pair is extracted.  

    Keyword Parameters:

    protocol
      The protocol to consider; one of: ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the clients belong; one or several of: ('world', 'dev', 'eval')
      The 'eval' group does not exist for protocol 'view1'.
      
    subworld
      The subset of the training data. Has to be specified if groups includes 'world' 
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').

    type
      One of ('restricted', 'unrestricted'). For 'restricted' type, only the **file ids**
      that appear in the file lists are returned, whereas the 'unrestricted' type returns
      **client ids** of the clients from "peoples.txt".

    Returns: A list containing all client names which have the desired properties.
    """

    self.__check_single__(protocol, 'protocol', self.m_valid_protocols)
    groups = self.__check_validity__(groups, 'group', self.m_valid_groups)
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_valid_subworlds)
    self.__check_single__(type, 'protocol type', self.m_valid_types)
    
    if type == 'unrestricted':
      return self.clients(protocol, groups, subworld)
    
    # the restricted case...
    queries = []
 
    # List of the models
    if protocol == 'view1':
      if 'world' in groups:
        queries.append(\
            self.m_session.query(File).join((Pair, or_(File.m_id == Pair.m_enrol_file, File.m_id == Pair.m_probe_file))).\
                  filter(Pair.m_protocol == 'train'))
      if 'dev' in groups:
        queries.append(\
            # enroll files
            self.m_session.query(File).join((Pair, File.m_id == Pair.m_enrol_file)).\
                  filter(Pair.m_protocol == 'test'))
    else:
      if 'world' in groups:
        # select training set for the given fold
        trainset = self.__world_for__(protocol, subworld)
        queries.append(\
            self.m_session.query(File).join((Pair, or_(File.m_id == Pair.m_enrol_file, File.m_id == Pair.m_probe_file))).\
                  filter(Pair.m_protocol.in_(trainset)))
      if 'dev' in groups:
        # select development set for the given fold
        devset = self.__dev_for__(protocol)
        queries.append(\
            self.m_session.query(File).join((Pair, File.m_id == Pair.m_enrol_file)).\
                  filter(Pair.m_protocol.in_(devset)))
      if 'eval' in groups:
        queries.append(\
            self.m_session.query(File).join((Pair, File.m_id == Pair.m_enrol_file)).\
                  filter(Pair.m_protocol == protocol))
        
    # all queries are made; now collect the file ids
    retval = []
    for query in queries: 
      for k in query:
        retval.append(k.m_id)
        
    # assure that the list of names is unique
    assert len(set(retval)) == len(retval)
    return retval


  def get_client_id_from_file_id(self, file_id):
    """Returns the client_id (real client id) attached to the given file_id
    
    Keyword Parameters:

    file_id
      The file_id to consider

    Returns: The client_id attached to the given file_id
    """
    q = self.m_session.query(File).\
          filter(File.m_id == file_id)

    assert q.count() == 1
    return q.first().m_client_id


  def objects(self, directory=None, extension=None, protocol=None, model_ids=None, groups=None, purposes=None, subworld='sevenfolds', type='restricted'):
    """Returns a set of filenames for the specific query by the user.

    Keyword Parameters:

    directory
      A directory name that will be prepended to the final filepath returned

    extension
      A filename extension that will be appended to the final filepath returned

    protocol
      The protocol to consider ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the objects belong ('world', 'dev', 'eval')

    purposes
      The purposes of the objects ('enrol', 'probe')

    subworld
      The subset of the training data. Has to be specified if groups includes 'world' 
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').
      
    type
      One of ('restricted', 'unrestricted'). If the type 'restricted' is given,
      model_ids will be handled as file ids, if type is 'unrestricted', model ids
      will be client ids.

    model_ids
      Only retrieves the objects for the provided list of model ids.  
      If 'None' is given (this is the default), no filter over 
      the model_ids is performed.

    Returns: A dictionary with the key "file_id" containing:
      - 0: the resolved filenames 
      - 1: the model id (for a probe image this is the model id of the corresponding model of the pair)
      - 2: the claimed client id attached to the model
      - 3: the real client id
      - 4: the "stem" path (basename of the file)

    considering all the filtering criteria. The keys of the dictionary are 
    unique identities for each file in the LFW database. Conserve these 
    numbers if you wish to save processing results later on.
    """
    
    self.__check_single__(protocol, "protocol", self.m_valid_protocols)
    groups = self.__check_validity__(groups, "group", self.m_valid_groups)
    purposes = self.__check_validity__(purposes, "purpose", self.m_valid_purposes)
    self.__check_single__(type, 'protocol type', self.m_valid_types)
    
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_valid_subworlds)
    
    if(isinstance(model_ids,str)):
      model_ids = (model_ids,)

    queries = []
    probe_queries = []
    file_alias = aliased(File)

    if protocol == 'view1':
      if 'world' in groups:
        # training files of view1
        if type == 'restricted':
          queries.append(\
              self.m_session.query(File).join((Pair, or_(File.m_id == Pair.m_enrol_file, File.m_id == Pair.m_probe_file))).\
                  filter(Pair.m_protocol == 'train'))
        else:
          queries.append(\
              self.m_session.query(File).join(People).\
                  filter(People.m_protocol == 'train'))
      if 'dev' in groups:
        # test files of view1
        if 'enrol' in purposes:
          queries.append(\
              self.m_session.query(File).join((Pair, File.m_id == Pair.m_enrol_file)).\
                  filter(Pair.m_protocol == 'test'))
        if 'probe' in purposes:
          probe_queries.append(\
              self.m_session.query(File, file_alias).\
                  join((Pair, File.m_id == Pair.m_probe_file)).\
                  join((file_alias, Pair.m_enrol_file == file_alias.m_id)).\
                  filter(Pair.m_protocol == 'test'))
          
    else:
      # view 2
      if 'world' in groups:
        # world set of current fold of view 2
        trainset = self.__world_for__(protocol, subworld)
        if type == 'restricted':
          queries.append(\
              self.m_session.query(File).join((Pair, or_(File.m_id == Pair.m_enrol_file, File.m_id == Pair.m_probe_file))).\
                  filter(Pair.m_protocol.in_(trainset)))
        else:
          queries.append(\
              self.m_session.query(File).join(People).\
                  filter(People.m_protocol.in_(trainset)))

      if 'dev' in groups:
        # development set of current fold of view 2
        devset = self.__dev_for__(protocol)
        if type == 'restricted':
          if 'enrol' in purposes:
            queries.append(\
                self.m_session.query(File).join((Pair, File.m_id == Pair.m_enrol_file)).\
                    filter(Pair.m_protocol.in_(devset)))
          if 'probe' in purposes:
            probe_queries.append(\
                self.m_session.query(File, file_alias).\
                    join((Pair, File.m_id == Pair.m_probe_file)).\
                    join((file_alias, file_alias.m_id == Pair.m_enrol_file)).\
                    filter(Pair.m_protocol.in_(devset)))
        else: # unrestricted
          # Note: This query is somewhat weird. You are allowed to use it, but it does not make much sense.
          queries.append(\
              self.m_session.query(File).join(People).\
                  filter(People.m_protocol.in_(devset)))

      if 'eval' in groups:
        # evaluation set of current fold of view 2; this is the REAL fold
        if type == 'restricted':
          if 'enrol' in purposes:
            queries.append(\
                self.m_session.query(File).join((Pair, File.m_id == Pair.m_enrol_file)).\
                    filter(Pair.m_protocol == protocol))
          if 'probe' in purposes:
            probe_queries.append(\
                self.m_session.query(File,file_alias).\
                    join((Pair, File.m_id == Pair.m_probe_file)).\
                    join((file_alias, file_alias.m_id == Pair.m_enrol_file)).\
                    filter(Pair.m_protocol == protocol))
        else: # unrestricted
          # Note: THIS QUERY VIOLATES THE LFW PROTOCOL. PLEASE DO NOT USE IT FOR EXPERIMENTS!  
          queries.append(\
              self.m_session.query(File).join(People).\
                  filter(People.m_protocol == protocol))
        
          
  
    retval = {}
    for query in queries:
      if model_ids and len(model_ids):
        if type == 'restricted': # filter file ids
          query = query.filter(File.m_id.in_(model_ids))
        else: # unrestricted; filter client ids
          query = query.filter(File.m_client_id.in_(model_ids))
          
      for f in query:
        retval[f.m_id] = (self.__make_path__(f.m_path, directory, extension), f.m_id, f.m_client_id, f.m_client_id, f.m_path)

    for query in probe_queries:
      if model_ids and len(model_ids):
        if type == 'restricted': # filter file ids
          query = query.filter(file_alias.m_id.in_(model_ids))
        else: # unrestricted; filter client ids
          query = query.filter(file_alias.m_client_id.in_(model_ids))
          
      for probe,model in query:
        retval[probe.m_id] = (self.__make_path__(probe.m_path, directory, extension), model.m_id, model.m_client_id, probe.m_client_id, probe.m_path)
      
    return retval

  def files(self, directory=None, extension=None, protocol=None, model_ids=None, groups=None, purposes=None, subworld='sevenfolds', type='restricted'):
    """Returns a dictionary of filenames for the specific query by the user.

    Keyword Parameters:

    directory
      A directory name that will be prepended to the final filepath returned

    extension
      A filename extension that will be appended to the final filepath returned

    protocol
      The protocol to consider ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the objects belong ('world', 'dev', 'eval')

    purposes
      The purposes of the objects ('enrol', 'probe')

    subworld
      If the single option 'restricted' is specified, only the 'world' files 
      that are given in the training pairs lists are returned  

    model_ids
      Only retrieves the objects for the provided list of model ids.  
      If 'None' is given (this is the default), no filter over 
      the model_ids is performed.

    Returns: A dictionary with the key "file_id" containing the resolved filenames 

    considering all the filtering criteria. The keys of the dictionary are 
    unique identities for each file in the LFW database. Conserve these 
    numbers if you wish to save processing results later on.
    """

    retval = {}
    d = self.objects(directory, extension, protocol, model_ids, groups, purposes, subworld, type)
    for k in d: retval[k] = d[k][0]

    return retval


  def pairs(self, directory=None, extension=None, protocol=None, groups=None, classes=None, subworld='sevenfolds'):
    """Returns a dictionary of pairs of files. 

    Keyword Parameters:

    directory
      A directory name that will be prepended to the final filepath returned

    extension
      A filename extension that will be appended to the final filepath returned

    protocol
      The protocol to consider ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the objects belong ('world', 'dev', 'eval')
      
    classes
      The classes to which the pairs belong ('matched', 'unmatched')

    Returns: A dictionary with the pair id as key, containing:
      - 0: the resolved filename 1
      - 1: the resolved filename 2
      - 2: client_id associated with filename 1
      - 3: client_id associated with filename 2
      - 4: file_id associated with filename 1
      - 5: file_id associated with filename 2

    considering all the filtering criteria. The keys of the dictionary are 
    unique identities for each file in the LFW database. Conserve these 
    numbers if you wish to save processing results later on.
    """

    def default_query():
      return self.m_session.query(Pair, File1, File2).\
                filter(File1.m_id == Pair.m_enrol_file).\
                filter(File2.m_id == Pair.m_probe_file)

    self.__check_single__(protocol, "protocol", self.m_valid_protocols)
    groups = self.__check_validity__(groups, "group", self.m_valid_groups)
    classes = self.__check_validity__(classes, "class", self.m_valid_classes)
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_valid_subworlds)

    queries = []
    File1 = aliased(File)
    File2 = aliased(File)

    if protocol == 'view1':
      if 'world' in groups:
        queries.append(default_query().filter(Pair.m_protocol == 'train'))
      if 'dev' in groups:
        queries.append(default_query().filter(Pair.m_protocol == 'test'))

    else:
      if 'world' in groups:
        trainset = self.__world_for__(protocol, subworld)
        queries.append(default_query().filter(Pair.m_protocol.in_(trainset)))
      if 'dev' in groups:
        devset = self.__dev_for__(protocol)
        queries.append(default_query().filter(Pair.m_protocol.in_(devset)))
      if 'eval' in groups:
        queries.append(default_query().filter(Pair.m_protocol == protocol))
          
    retval = {}
    for query in queries:
      if not 'matched' in classes:
        query = query.filter(Pair.m_is_match == False)
      if not 'unmatched' in classes:
        query = query.filter(Pair.m_is_match == True)

      for pair,file1,file2 in query:
        retval[pair.m_id] = (\
          self.__make_path__(file1.m_path, directory, extension),\
          self.__make_path__(file2.m_path, directory, extension),\
          file1.m_client_id,\
          file2.m_client_id,\
          file1.m_id,\
          file2.m_id)
        
    return retval


  def save_one(self, file_id, obj, directory, extension):
    """Saves a single object supporting the bob save() protocol.

    This method will call save() on the the given object using the correct
    database filename stem for the given id.
    
    Keyword Parameters:

    file_id
      The file id of the object in the database.

    obj
      The object that needs to be saved, respecting the bob save() protocol.

    directory
      This is the base directory to which you want to save the data. The
      directory is tested for existence and created if it is not there with
      os.makedirs()

    extension
      The extension determines the way each of the arrays will be saved.
    """

    import os
    from bob.io import save

    fobj = self.m_session.query(File).filter_by(m_id=file_id).one()
    fullpath = os.path.join(directory, str(fobj.m_path) + extension)
    fulldir = os.path.dirname(fullpath)
    utils.makedirs_safe(fulldir)
    save(obj, fullpath)

  def save(self, data, directory, extension):
    """This method takes a dictionary of blitz arrays or bob.database.Array's
    and saves the data respecting the original arrangement as returned by
    files().

    Keyword Parameters:

    data
      A dictionary with two keys 'real' and 'attack', each containing a
      dictionary mapping file ids from the original database to an object that
      supports the bob "save()" protocol.

    directory
      This is the base directory to which you want to save the data. The
      directory is tested for existence and created if it is not there with
      os.makedirs()

    extension
      The extension determines the way each of the arrays will be saved.
    """    

    for key, value in data:
      self.save_one(key, value, directory, extension)
