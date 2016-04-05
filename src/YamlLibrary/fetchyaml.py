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

    def get_tree(self, yml_src, key):
        """return a python dictionary with subset of data filter by 'key'"""
        dct = self._smart_load(yml_src)
        return self._get_tree_by_smart_path(dct, key)

    def compare_tree(self, src, dst):
        """Recursively compare 'src' (json-like dict/list tree) with
        matcher 'dst' (same tree structure and keys, except value part are value/expr/regex).
        src: a python dictionary holding yaml/json/bsop data
        dst: a subset of above python dictionary, with values in string/number/math-expr/regex
        return: True or False
        """
        if isinstance(dst, dict):
            return self._cmp_dict(src, dst)
        elif isinstance(dst, (list, tuple)):
            return self._cmp_list(src, dst)
        elif isinstance(dst, (int, long, float)):
            return self._cmp_number(src, dst)
        elif isinstance(dst, bool):
            return self._cmp_bool(src, dst)
        elif isinstance(dst, basestring):
            if len(dst.split('y')) > 1:
                logger.debug("compare_tree: eval '%s' with %s instead of y" % (str(dst), str(src)))
                return self._eval_math_expr(src, dst)
            return self._cmp_string(src, dst)
        logger.debug("compare_tree: src not in [dict, list, basestring, int, long, float, bool]:\n%s" % str(src))
        return False

    def nodes_should_match(self, yml_doc_data, yml_path, yml_doc_matcher):
        dct = self._smart_load(yml_doc_data)
        src = self._get_tree_by_smart_path(dct, yml_path)
        dst = self._smart_load(yml_doc_matcher)
        if not self.compare_tree(src, dst):
            raise AssertionError("nodes under '%s' do not satisfied matcher:\nactual:\n'%s'\nmatcher:\n'%s'" %
                                 (yml_path, str(src), str(dst)))

    @staticmethod
    def _smart_load(src):
        if isinstance(src, basestring):
            try:
                dct = yaml.load(src)
            except:
                raise ("_smart_load: can not do yaml load: %s" % src)
        elif isinstance(src, (dict, list)):
            try:
                dct = yaml.load(yaml.dump(src))
            except:
                raise ("_smart_load: Can not convert to yaml data format: %s" % str(src))
        else:
            raise ("_smart_load: Unknown format to yaml: %s" % str(src))
        return dct

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
        if key == '.' or key == '/':
            return dct
        s = key
        sp = re.split('[%/]', s, 2)  # path_left, middle_locator, path_right
        while len(sp) == 3:
            left, locator, right = sp
            logger.debug("_smart_path: path divided as:\nleft='%s'\nmiddle='%s'\nright='%s'" % (left, locator, right))
            blocks = self._get_tree_by_direct_path(dct, self._tokenize(left)) if left else dct
            logger.debug("_smart_path: get tree/node by left path (%s): \n%s" % (left, str(blocks)))
            if not blocks:
                logger.debug("_smart_path: Can not get parent list '%s'" % left)
                return None
            if not isinstance(blocks, list):
                raise TypeError("_smart_path: Node is not a list: %s" % left)
            if len(blocks) == 0:
                logger.debug("_smart_path: Node is an empty list: %s" % left)
                return None
            psv = re.split('(~|=)', locator)
            if not isinstance(psv, list) or len(psv) < 3:
                raise ValueError("_smart_path: expect 'sub-path=value or sub-path~regex' but received '%s'" % locator)
            path, sign, expr = psv
            index = -1
            for i, block in enumerate(blocks):
                v = self._get_tree_by_direct_path(block, self._tokenize(path))
                logger.debug("_smart_path: get tree/node by sub-path (%s), value: \n'%s'" % (path, str(v)))
                if not v: continue
                if not isinstance(v, (basestring, bool, int, float)):
                    raise ValueError("_smart_path: expect basic type to index block but received '%s'" % left)
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
            logger.debug("_smart_path: '%s' indexed as '%d', new path will be '%s'" % (locator, index, s))
            sp = re.split('%', s, 2)
        if len(sp) == 1:
            return self._get_tree_by_direct_path(dct, self._tokenize(s))
        return None

    @staticmethod
    def _cmp_string(src, dst):
        if not isinstance(src, basestring):
            logger.debug("_cmp_string: receives non-string: %s" % str(src))
            return False
        if dst[0] != '~':
            if unicode(src) == unicode(dst):
                return True
            logger.debug("_cmp_string: string not equal: %s == %s" % (unicode(src), unicode(dst)))
        if dst[0] == '~':
            if re.compile(dst[1:]).search(src):
                return True
            logger.debug("_cmp_string: string not match: %s ~ %s" % (src, dst))
        return False

    @staticmethod
    def _cmp_number(src, dst):
        for t in (int, long, float, bool):
            if isinstance(dst, t):
                try:
                    if t(src) == t(dst):
                        return True
                except:
                    logger.debug("_cmp_number: expect type %s but get %s" % (str(type(dst)), str(type(src))))
                    logger.debug("_cmp_number: Can not convert: %s" % str(src))
        logger.debug("_cmp_number: number '%s' not equal to '%s'" % (str(src), str(dst)))
        return False

    @staticmethod
    def _cmp_bool(src, dst):
        try:
            if bool(src) == bool(dst):
                return True
        except:
            logger.debug("_cmp_bool: expect bool but get %s" % str(type(src)))
            logger.debug("_cmp_bool: Can not convert to bool: %s" % str(src))
        return False

    @staticmethod
    def _eval_math_expr(src, dst):
        if not isinstance(src, (int, long, float)):
            logger.debug("_eval_math_expr: receives src non-int/long/float: %s" % str(src))
            return False
        for t in (int, long, float):
            if isinstance(src, t) and eval(str(t(src)).join(dst.split('y'))):
                return True
        logger.debug("_eval_math_expr: '%s' not satisfied math expr '%s'" % (str(src), dst))
        return False

    def _cmp_dict(self, src, dst):
        if not isinstance(dst, dict):
            logger.debug("_cmp_dict: '%s' is not a dict" % str(dst))
            return False
        try:
            for key in dst.keys():
                if not self.compare_tree(src[key], dst[key]):
                    return False
        except KeyError:
            logger.debug("_cmp_dict: matcher key '%s' not found in '%s'" % (str(key), str(src)))
            return False
        return True

    def _cmp_list(self, src, dst):
        if not isinstance(dst, (tuple,list)):
            logger.debug("_cmp_list: '%s' is not a list or tuple" % str(dst))
            return False
        try:
            for i in range(len(dst)):
                if not self.compare_tree(src[i], dst[i]):
                    return False
        except IndexError:
            logger.debug("_cmp_list: matcher index '%s' out of range in list '%s'" % (str(key), str(src)))
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
                raise ValueError("_direct_path: list index not a integer: %r." % head)
            try:
                value = dct[idx]
            except IndexError:
                raise IndexError("_direct_path: list index out of range: %d to %d." % (idx, len(dct)))
        else:
            try:
                value = dct[head]
            except KeyError:
                raise KeyError("_direct_path: dict misses key %r." % (head, ))
            except:
                raise TypeError("_direct_path: can't query sub-value '%r' of a leaf with value '%r'." % (head, dct))
        return self._get_tree_by_direct_path(value, key)

