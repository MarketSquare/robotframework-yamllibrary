#!/usr/bin/env python
import yaml
import re
from robot.api import logger


class FetchYaml(object):
    """
    FetchYaml is a library to fetch sub-document from yaml doc tree, compare it with a matcher doc tree
    it requires string buffer input that can be loaded by yaml.load() function
    """
    def __init__(self):
        pass

    def get_tree(self, yml_string, key):
        """return a python dictionary with subset of data filter by 'key'"""
        if isinstance(yml_string, basestring):
            try:
                dct = yaml.load(yml_string)
            except:
                raise ("can not do yaml load: %s" % yml_string)
        elif isinstance(yml_string, (dict, list)):
            try:
                dct = yaml.load(yaml.dump(yml_string))
            except:
                raise ("Can not convert to yaml data format: %s" % str(yml_string))
        else:
            raise ("Unknown format to yaml: %s" % str(yml_string))
        return self._get_tree_by_smart_path(dct, key)

    def compare_tree(self, src, dst):
        """Recursively compare 'src' (json-like dict/list tree) with
        matcher 'dst' (same tree structure and keys, except value part are value/expr/regex).
        src: a python dictionary holding yaml/json/bsop data
        dst: a subset of above python dictionary, with values in value/expr/regex format
        return: True or False
        """
        if isinstance(src, dict):
            return self._cmp_dict(src, dst)
        elif isinstance(src, (list, tuple)):
            return self._cmp_list(src, dst)
        elif isinstance(src, basestring):
            return self._cmp_string(src, dst)
        elif isinstance(src, (int, float)):
            return self._eval_numbers(src, dst)
        elif isinstance(src, bool):
            return src == bool(dst)
        logger.debug("src not in [dict, list, basestring, int, float, bool]:\n%s" % str(src))
        return False

    def nodes_should_match(self, yml_doc_data, yml_path, yml_doc_matcher):
        dct = yaml.load(yml_doc_data)
        src = self._get_tree_by_smart_path(dct, yml_path)
        dst = yaml.load(yml_doc_matcher)
        if not self.compare_tree(src, dst):
            raise AssertionError("nodes under '%s' do not satisfied matcher:\nactual:\n'%s'\nmatcher:\n'%s'" %
                                 (yml_path, str(src), yml_doc_matcher))

    @staticmethod
    def _tokenize(s):
        if s is None:
            raise StopIteration
        tokens = (re.sub(r'\\(\\|\.)', r'\1', m.group(0))
                  for m in re.finditer(r'((\\.|[^.\\])*)', s))
        # an empty string superfluous token is added after all non-empty token
        for token in tokens:
            if len(token) != 0:
                next(tokens)
            yield token

    def _get_tree_by_smart_path(self, dct, key):
        s = key
        sp = re.split('[%/]', s, 2)  # path_left, middle_locator, path_right
        while len(sp) == 3:
            left, locator, right = sp
            logger.debug("path divided as:\nleft='%s'\nmiddle='%s'\nright='%s'" % (left, locator, right))
            blocks = self._get_tree_by_direct_path(dct, self._tokenize(left)) if left else dct
            logger.debug("get tree/node by left path (%s): \n%s" % (left, str(blocks)))
            if not blocks:
                logger.debug("Can not get parent list '%s'" % left)
                return None
            if not isinstance(blocks, list):
                raise TypeError("Node is not a list: %s" % left)
            if len(blocks) == 0:
                logger.debug("node is an empty list: %s" % left)
                return None
            psv = re.split('(~|=)', locator)
            if not isinstance(psv, list) or len(psv) < 3:
                raise ValueError("expect 'subpath=value or subpath~regex' but received '%s'" % locator)
            path, sign, expr = psv
            index = -1
            for i, block in enumerate(blocks):
                v = self._get_tree_by_direct_path(block, self._tokenize(path))
                logger.debug("get tree/node by sub-path (%s), value: \n'%s'" % (path, str(v)))
                if not v: continue
                if not isinstance(v, (basestring, bool, int, float)):
                    raise ValueError("expect basic type to index block but received '%s'" % left)
                index = i
                if sign == '~' and re.compile(expr).search(v): break
                if sign == '=':
                    if isinstance(v, basestring) and unicode(v) == expr: break
                    if isinstance(v, int) and v == int(expr): break
                    if isinstance(v, float) and v == float(expr): break
                    if isinstance(v, bool) and v == bool(expr): break
                index = -1
            if index < 0:
                return None
            s = '.'.join((left, str(index))) if left else str(index)
            s = '.'.join((s, right)) if right else s
            logger.debug("'%s' indexed as '%d', new path will be '%s'" % (locator, index, s))
            sp = re.split('%', s, 2)
        if len(sp) == 1:
            return self._get_tree_by_direct_path(dct, self._tokenize(s))
        return None

    @staticmethod
    def _cmp_string(src, dst):
        matcher = dst if isinstance(dst, basestring) else str(dst)
        if matcher[0] != '~' and unicode(src) == unicode(matcher):
            return True
        if matcher[0] == '~' and re.compile(matcher[1:]).search(src):
            return True
        logger.debug("'%s' not satisfied '%s'" % (src, matcher))
        return False

    @staticmethod
    def _eval_numbers(src, dst):
        if isinstance(dst, (int, float)):
            if src == dst:
                return True
            logger.debug("'%f' not equal to '%f'" % (src, dst))
        if isinstance(dst, basestring):
            parts = dst.split()
            for i in range(len(parts)):
                if parts[i] == 'x':
                    parts[i] = str(src)
            if eval(''.join(parts)):
                return True
            logger.debug("'%f' not satisfied '%s'" % (src, dst))
        return False

    def _cmp_dict(self, src, dst):
        if not isinstance(dst, dict):
            logger.debug("'%s' is not a dict" % str(dst))
            return False
        try:
            for key in dst.keys():
                if not self.compare_tree(src[key], dst[key]):
                    return False
        except KeyError:
            logger.debug("matcher key '%s' not found in '%s'" % (str(key), str(src)))
            return False
        return True

    def _cmp_list(self, src, dst):
        if not isinstance(dst, (tuple,list)):
            logger.debug("'%s' is not a list or tuple" % str(dst))
            return False
        try:
            for i in range(len(dst)):
                if not self.compare_tree(src[i], dst[i]):
                    return False
        except IndexError:
            logger.debug("matcher index '%s' out of range in list '%s'" % (str(key), str(src)))
            return False
        return True

    def _get_tree_by_direct_path(self, dct, key):
        key = iter(key)
        try:
            head = next(key)
        except StopIteration:
            return dct
        if isinstance(dct, list):
            try:
                idx = int(head)
            except ValueError:
                raise ValueError("list index not a integer: %r." % head)
            try:
                value = dct[idx]
            except IndexError:
                raise IndexError("list index out of range: %d to %d." % (idx, len(dct)))
        else:
            try:
                value = dct[head]
            except KeyError:
                raise KeyError("dict misses key %r." % (head, ))
            except:
                raise TypeError("can't query sub-value '%r' of a leaf with value '%r'." % (head, dct))
        return self._get_tree_by_direct_path(value, key)

