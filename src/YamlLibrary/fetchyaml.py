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
        self._mathexpr = re.compile("^[y>=< 0-9]+$")

    def get_tree(self, yml_src, path):
        """travel given 'path' in src to return a sub-tree that may
         be a single python dictionary, a list of dictionaries, or
         a single node (the value from a key/value pair)
        """
        dct = self._smart_load(yml_src)
        return self._get_tree_by_smart_path(dct, path)

    def compare_tree(self, src, dst):
        """Recursively compare 'src' (json-like dict/list tree) with
        matcher 'dst' (same tree structure and keys, except value part are value/expr/regex).

        src: a python dictionary holding yaml/json/bson data

        dst: a subset of above python dictionary, with values in string/number/math-expr/regex
        
        return: True or False
        """
        if dst is None or (isinstance(dst, (list, tuple, dict, basestring)) and len(dst) == 0):
            return self._cmp_null(src, dst)
        elif isinstance(dst, (list, tuple)):
            return self._cmp_list(src, dst)
        elif isinstance(dst, dict):
            return self._cmp_dict(src, dst)
        elif isinstance(dst, basestring) and self._mathexpr.search(dst) and len(dst.split('y')) > 1:
            logger.debug("compare_tree: eval '%s' with %s instead of y" % (str(dst), str(src)))
            return self._eval_math_expr(src, dst)
        elif isinstance(dst, (basestring, bool, int, long, float)):
            return self._cmp_base_types(src, dst)
        logger.debug("compare_tree: src not in [dict, list, basestring, int, long, float, bool]:\n%s" % str(src))
        return False

    def nodes_should_match(self, yml_doc_data, yml_path, yml_doc_matcher):
        """compare sub-tree from given yaml path against a yaml tree of matcher.

        A matcher could be 'direct_value' for equal matching, '~regex' for regression
        expression matching, or a 'y'-variable math regression for evaluating (python eval)

        for example: {'age': 30, 'name': '~^Smith .+', 'salary': 'y > 20000'}

        Return False if any matcher fails.

        Return True if all matchers succeed.
        """
        dct = self._smart_load(yml_doc_data)
        src = self._get_tree_by_smart_path(dct, yml_path)
        dst = self._smart_load(yml_doc_matcher)
        if not self.compare_tree(src, dst):
            raise AssertionError("nodes under '%s' do not satisfied matcher:\nactual:\n'%s'\nmatcher:\n'%s'" %
                                 (yml_path, str(src), str(dst)))

    @staticmethod
    def _smart_load(src):
        if src is None or isinstance(src, (int, long, float, bool)):
            return src
        if isinstance(src, basestring):
            try:
                return yaml.load(src)
            except:
                return yaml.load(src.replace('\/', '/'))
        if isinstance(src, (dict, list)):
            return yaml.load(yaml.dump(src))
        raise ValueError("_smart_load: Unknown format to yaml: %s (type is %s)" % (str(src), str(type(src))))

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
            logger.debug("_smart_path: split path to left/middle/right: '%s', '%s', '%s'" % (left, locator, right))
            blocks = self._get_tree_by_direct_path(dct, self._tokenize(left)) if left else dct
            logger.debug("_smart_path: get tree/node by left path '%s':\n%s" % (left, str(blocks)))
            if not blocks:
                logger.debug("_smart_path: Can not get parent list '%s'" % left)
                return None
            if not isinstance(blocks, (list, dict)):
                raise TypeError("_smart_path: Node is not a list or dictionary: %s" % left)
            if len(blocks) == 0:
                logger.debug("_smart_path: Node is an empty list: %s" % left)
                return None
            psv = re.split('(~|=)', locator)
            if not isinstance(psv, list) or len(psv) < 3:
                raise ValueError("_smart_path: expect 'sub-path=value or sub-path~regex' but received '%s'" % locator)
            path, sign, expr = psv
            index = -1
            search_pairs = blocks.iteritems() if isinstance(blocks, dict) else enumerate(blocks)
            for i, block in search_pairs:
                v = self._get_tree_by_direct_path(block, self._tokenize(path))
                logger.debug("_smart_path: get tree/node by sub-path '%s', value:\n'%s'" % (path, str(v)))
                if not v: continue
                if not isinstance(v, (basestring, bool, int, long, float)):
                    raise ValueError("_smart_path: expect basic type to index block but received '%s'" % left)
                index = 1
                if sign == '~' and re.compile(expr).search(v): break
                if sign == '=':
                    if isinstance(v, basestring) and unicode(v) == expr: break
                    if isinstance(v, int) and v == int(expr): break
                    if isinstance(v, long) and v == long(expr): break
                    if isinstance(v, float) and v == float(expr): break
                    if isinstance(v, bool) and v == bool(expr): break
                index = -1
            if index < 0:
                return None
            s = '.'.join((left, str(i))) if left else str(i)
            s = '.'.join((s, right)) if right else s
            logger.debug("_smart_path: '%s' indexed as '%d', new path will be '%s'" % (locator, index, s))
            sp = re.split('[/%]', s, 2)
        if len(sp) < 3:
            return self._get_tree_by_direct_path(dct, self._tokenize(s))
        return None

    @staticmethod
    def _cmp_string(src, dst):
        if not isinstance(src, basestring):
            logger.debug("_cmp_string: receives non-string: %s" % str(src))
            return False
        if len(dst) == 0:
            return len(src) == 0
        if dst[0] != '~':
            if len(src) == len(dst) and unicode(src) == unicode(dst):
                return True
        if dst[0] == '~':
            if len(dst) < 2:
                logger.debug("_cmp_string: regexp is empty!")
                return False
            if re.compile(dst[1:]).search(src):
                logger.debug("_cmp_string: src '%s' matches regexp '%s'" % (str(src), str(dst)))
                return True
            logger.debug("_cmp_string: string not match regexp: %s ~ %s" % (src, dst))
        return False

    @staticmethod
    def _cmp_number(src, dst):
        for t in (int, long, float):
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
    def _cmp_null(src, dst=None):
        if src is None:
            return True
        if isinstance(src, basestring) and src in ('', 'null', 'undefined'):
            return True
        if isinstance(src, (list, tuple, dict, basestring)) and len(src) == 0:
            return True
        logger.debug("_cmp_null: src=[%s] does not matches None" % str(src))
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
        if not isinstance(src, dict):
            logger.debug("_cmp_dict: src tree '%s' is not a dict" % str(src))
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
        if not isinstance(src, (tuple, list)):
            logger.debug("_cmp_list: src '%s' is not a list or tuple" % str(src))
            return False
        try:
            for v in dst:
                if v is None or isinstance(v, (basestring, int, long, float, bool)):
                    if all([not self._cmp_base_types(s, v) for s in src]):
                        logger.debug("_cmp_list: '%s' from '%s' not match any value in list '%s'"
                                     % (str(v), str(dst), str(src)))
                        return False
                elif all([not self.compare_tree(s, v) for s in src]):
                    logger.debug("_cmp_list: item '%s' from '%s' not found in src list '%s'"
                                 % (str(v), str(dst), str(src)))
                    return False
        except IndexError:
            logger.debug("_cmp_list: matcher index '%s' out of range in list '%s'" % (str(key), str(src)))
            return False
        logger.debug("_cmp_list: src '%s' matches '%s'" % (str(src), str(dst)))
        return True

    def _cmp_base_types(self, src, dst):
        if dst is None:
            return self._cmp_null(src, dst)
        if isinstance(dst, bool):
            return self._cmp_bool(src, dst)
        elif isinstance(dst, (int, long, float)):
            return self._cmp_number(src, dst)
        elif isinstance(dst, basestring):
            return self._cmp_string(src, dst)
        logger.debug("Unknown type of dst: %s" % str(dst))

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
        for ty in (int, long, float, bool):
            if isinstance(value, ty):
                value = ty(value)
                break
        return self._get_tree_by_direct_path(value, key)

    def _strip_bson_id(self, dct):
        if isinstance(dct, (list, tuple)):
           for child in dct:
                self._strip_bson_id(child)
        if isinstance(dct, dict):
            for key in dct.keys():
                if key == '_id':
                    del dct['_id']
                if isinstance(dct[key], dict):
                    self._strip_bson_id(dct[key])

    @staticmethod
    def _strip_number_long(s):
        rex = re.compile('^NumberLong\(([0-9]+)\)$')
        result = rex.search(s)
        return result.group(1) if result else s
