"""
feature_tree.py — Core FeatureTree Data Structure

Defines TreeNode, IndexNode, BodyNode, IndexTree, BodyTree, FeatureTree
and the construction functions that convert an openpyxl sheet into a
hierarchical tree representation.
"""

import time
import pickle
from loguru import logger

from utils.sheet_utils import delete_dict_none_none
from utils.constants import DEFAULT_TABLE_NAME
from table2tree.extract_excel import get_structured_xlsx_sheet

def serial(level_list):
    s = ""
    for i in level_list:
        s += str(i) + "."
    return s[:-1]


class TreeNode:

    def __init__(self, value=None):
        self.value = value  # string or subtree
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)

    def remove_child(self, child_node):
        if child_node in self.children:
            self.children.remove(child_node)


class IndexNode(TreeNode):

    def __init__(self, value=None):
        super().__init__(value)
        self.body = []
        self.father = None

    def add_body_node(self, node):
        self.body.append(node)


class BodyNode(TreeNode):

    def __init__(self, value=None):
        super().__init__(value)
        self.father = []
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None

    def get_pos(self):
        return [self.x1, self.y1, self.x2, self.y2]

    def add_father(self, node):
        self.father.append(node)


def get_leaf_nodes(root: TreeNode):
    """Return all leaf nodes of the tree as a list."""
    if not root:
        return []

    if len(root.children) <= 0:
        return [root]

    leaves = []
    for child in root.children:
        leaves.extend(get_leaf_nodes(child))

    return leaves


class IndexTree:

    def __init__(self):
        self.root = IndexNode()
        self.leaf_nodes = []

    def add_index(self, node: IndexNode):
        node.father = self.root
        self.root.add_child(node)
        self.leaf_nodes.extend(get_leaf_nodes(node))

    def add_leaf_body_node_by_pos(self, body_node, pos):
        try:
            if pos < 0 or pos >= len(self.leaf_nodes):
                return  # 索引越界，直接返回
            leaf : IndexNode = self.leaf_nodes[pos]
            leaf.add_body_node(body_node)
        except Exception as e:
            print(body_node.value)
            import traceback; traceback.print_exc()

    def value_list(self):
        res_list = []

        node = self.root.children[:]
        while len(node) > 0:
            curr : IndexNode = node[0]
            res_list.append(curr.value)
            node.extend(curr.children)
            node = node[1:]

        return res_list

    def get_flatten_schema(self):
        schema_list = []

        def dfs(i_node: IndexNode, path: list):
            if not i_node:
                return
            if i_node != self.root:
                path.append(str(i_node.value))

            if len(i_node.children) <= 0:
                schema = "-".join(path)
                if schema in schema_list:
                    index = 1
                    while f"{schema}{index}" in schema_list:
                        index += 1
                    schema_list.append(f"{schema}{index}")
                else:
                    schema_list.append(schema)
            else:
                for node in i_node.children:
                    dfs(node, path[:])

        dfs(self.root, [])
        return schema_list


class BodyTree:

    def __init__(self):
        self.root = BodyNode()

    def add_deep(self, node: BodyNode):
        t = self.root
        while len(t.children) > 0:
            t = t.children[0]
        t.add_child(node)
        node.add_father(t)

    def value_list(self):
        res_list = []

        node = self.root.children[:]
        while len(node) > 0:
            curr : BodyNode = node[0]
            if curr.value not in res_list:
                res_list.append(curr.value)
            node.extend(curr.children)
            node = node[1:]

        return res_list


class FeatureTree:

    def __init__(self, index_tree: IndexTree = None, body_tree: BodyTree = None):
        self.index_tree = index_tree
        self.body_tree = body_tree

    def load_from_pkl(self, pkl_file):
        try:
            with open(pkl_file, "rb") as f:
                f_tree: FeatureTree = pickle.load(f)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            return None
        return f_tree

    def all_value_list(self):
        return self.index_value_list() + self.body_value_list()

    def get_list_value(self, pos):
        ncols = len(self.index_tree.leaf_nodes)
        if pos < 0 or pos >= ncols:
            return []

        value_list = []
        for b_node in self.index_tree.leaf_nodes[pos].body:
            value_list.append(b_node.value)
        return value_list

    def index_value_list(self):
        res_list = []

        flag = False
        for index_node in self.index_tree.leaf_nodes:
            if (
                len(index_node.body) >= 1
                and type(index_node.body[0].value) == FeatureTree
            ):
                flag = True
                break

        if flag:
            for index_node in self.index_tree.leaf_nodes:
                for body_node in index_node.body:
                    if type(body_node.value) == FeatureTree:
                        res = body_node.value.index_value_list()
                        res_list.extend(res)
        res_list = [x for x in res_list if x is not None and len(str(x)) > 0]
        res_list.extend(self.index_tree.value_list())
        return res_list

    def body_value_list(self):
        res_list = []

        flag = False
        for index_node in self.index_tree.leaf_nodes:
            if (
                len(index_node.body) >= 1
                and type(index_node.body[0].value) == FeatureTree
            ):
                flag = True
                break
        if flag:
            for index_node in self.index_tree.leaf_nodes:
                if len(index_node.body) >= 1:
                    if type(index_node.body[0].value) == FeatureTree:
                        res = index_node.body[0].value.body_value_list()
                        res_list.extend(res)
                    else:
                        res_list.append(index_node.body[0].value)
        else:
            res_list.extend(self.body_tree.value_list())
        res_list = [x for x in res_list if x is not None and len(str(x)) > 0]
        return res_list

    def get_max_row(self):
        return max([len(leaf.body) for leaf in self.index_tree.leaf_nodes])

    def get_max_col(self):
        return len(self.index_tree.leaf_nodes)

    def get_structured_table(self):
        """Return structured table in list format."""
        schema = self.index_tree.get_flatten_schema()
        data = []
        return [schema] + data

    def __index__(self):
        """Return a JSON dict with keys only (values set to None or schema list)."""
        json_dict = {}
        flag = False
        for index_node in self.index_tree.leaf_nodes:
            if (
                len(index_node.body) >= 1
                and type(index_node.body[0].value) == FeatureTree
            ):
                flag = True
                break
        if flag:
            for index_node in self.index_tree.leaf_nodes:
                if len(index_node.body) >= 1:
                    if type(index_node.body[0].value) == FeatureTree:
                        res = index_node.body[0].value.__index__()
                        if DEFAULT_TABLE_NAME in res:
                            json_dict[index_node.value] = res[DEFAULT_TABLE_NAME]
                        else:
                            json_dict[index_node.value] = res
                    else:
                        json_dict[index_node.value] = "String"
                    if (
                        type(json_dict[index_node.value]) == list
                        and len(json_dict[index_node.value]) == 1
                    ):
                        json_dict[index_node.value] = json_dict[index_node.value][0]
        else:
            schema = self.index_tree.get_flatten_schema()
            json_dict[DEFAULT_TABLE_NAME] = schema
        return json_dict

    def __json__(self):
        """Serialize the tree to a JSON-compatible dict."""
        json_dict = {}
        flag = False
        for index_node in self.index_tree.leaf_nodes:
            if (
                len(index_node.body) >= 1
                and type(index_node.body[0].value) == FeatureTree
            ):
                flag = True
                break
        if flag:  # key-value form
            for index_node in self.index_tree.leaf_nodes:
                if len(index_node.body) >= 1:
                    if type(index_node.body[0].value) == FeatureTree:
                        res = index_node.body[0].value.__json__()
                        if DEFAULT_TABLE_NAME in res:
                            json_dict[index_node.value] = res[DEFAULT_TABLE_NAME]
                        else:
                            json_dict[index_node.value] = res
                    else:
                        json_dict[index_node.value] = index_node.body[0].value
                    if (
                        type(json_dict[index_node.value]) == list
                        and len(json_dict[index_node.value]) == 1
                    ):
                        json_dict[index_node.value] = json_dict[index_node.value][0]
        else:  # list form
            res = []
            schema_list = self.index_tree.get_flatten_schema()

            def dfs(b_node, path, x1, x2):
                if not b_node:
                    return
                if b_node != self.body_tree.root:
                    if x1 is not None and b_node.x1 is not None:
                        x1 = max(x1, b_node.x1)
                    if x2 is not None and b_node.x2 is not None:
                        x2 = min(x2, b_node.x2)
                    path.append(b_node)

                if len(b_node.children) <= 0:
                    if len(schema_list) == len(path):  # one row
                        tmp_dict = {}
                        for k, v in zip(schema_list, path):
                            tmp_dict[k] = str(v.value)
                        res.append(tmp_dict)
                    return
                else:
                    for node in b_node.children:
                        if (
                            x1 is not None
                            or x2 is not None
                            or node.x1 is not None
                            or node.x2 is not None
                            or (node.x1 <= x2 and node.x2 >= x1)
                        ):
                            dfs(node, path[:], x1, x2)

            max_x2 = 0
            for b_node in self.body_tree.root.children:
                if b_node.x2 is not None:
                    max_x2 = max(max_x2, b_node.x2)

            dfs(self.body_tree.root, [], 1, max_x2)
            json_dict[DEFAULT_TABLE_NAME] = res
            
            json_dict = delete_dict_none_none(json_dict)
        return json_dict

    def __str__(self, level_list=[1]):
        s = ""
        for index in self.index_tree.leaf_nodes:
            s = s + serial(level_list) + " " + str(index.value) + ": "
            for body_node in index.body:
                if isinstance(body_node.value, FeatureTree):
                    s = s + "\n" + body_node.value.__str__(level_list + [1])
                else:
                    s = s + str(body_node.value) + ", "
            s += "\n"
            level_list[-1] += 1
        return s

def construct_index_tree(schema_sheet):
    from utils.sheet_utils import get_merge_cell_size, single_cell, get_sub_sheet

    nrows = schema_sheet.max_row
    ncols = schema_sheet.max_column

    index_tree = IndexTree()

    col = 1
    while col <= ncols:
        cell = schema_sheet.cell(row=1, column=col)
        x1, y1, x2, y2 = get_merge_cell_size(schema_sheet, cell.coordinate)

        if not single_cell(schema_sheet, x1, y1, nrows, y2):
            sub_schema_sheet = get_sub_sheet(schema_sheet, x2 + 1, y1, nrows, y2)
            sub_index_tree = construct_index_tree(sub_schema_sheet)
            index_node = sub_index_tree.root
            index_node.value = schema_sheet.cell(row=x1, column=y1).value
        else:
            index_node = IndexNode(schema_sheet.cell(row=x1, column=y1).value)
        index_tree.add_index(index_node)

        col += y2 - y1 + 1

    return index_tree


def _detect_column_groups(sheet, row, start_col, end_col):
    """Detect groups of columns with same value (conceptual merges) in a flattened sheet."""
    groups = []
    col = start_col
    
    while col <= end_col:
        cell_val = sheet.cell(row=row, column=col).value
        group_start = col
        
        # Find the extent of this group (consecutive cells with same value)
        while col < end_col:
            next_val = sheet.cell(row=row, column=col + 1).value
            if next_val != cell_val:
                break
            col += 1
        
        groups.append((group_start, col, cell_val))
        col += 1
    
    return groups


def _is_title_row_in_schema(sheet, row, start_col, end_col):
    """Check if a row is a title row (80%+ of cells have same non-empty value)."""
    first_val = sheet.cell(row=row, column=start_col).value
    if first_val is None or str(first_val).strip() == '':
        return False
    
    same_count = 0
    total_cols = end_col - start_col + 1
    
    for col in range(start_col, end_col + 1):
        if sheet.cell(row=row, column=col).value == first_val:
            same_count += 1
    
    # 80% threshold for title row detection
    return same_count >= total_cols * 0.8


def _has_merge_info(sheet):
    """Check if sheet has any merged cell ranges."""
    return len(list(sheet.merged_cells.ranges)) > 0


def construct_index_tree_flattened(schema_sheet, start_row=1, start_col=1, end_col=None):
    """Construct index tree from a flattened sheet (no merge info) using value-based grouping."""
    from utils.sheet_utils import get_sub_sheet
    
    nrows = schema_sheet.max_row
    ncols = schema_sheet.max_column
    if end_col is None:
        end_col = ncols
    
    index_tree = IndexTree()
    
    # Skip title rows (rows where 80%+ of cells have the same value)
    current_row = start_row
    while current_row <= nrows and _is_title_row_in_schema(schema_sheet, current_row, start_col, end_col):
        current_row += 1
    
    if current_row > nrows:
        # All rows were title rows - create a simple leaf node
        val = schema_sheet.cell(row=nrows, column=start_col).value
        index_node = IndexNode(val)
        index_tree.add_index(index_node)
        return index_tree
    
    # Detect column groups in the current row
    groups = _detect_column_groups(schema_sheet, current_row, start_col, end_col)
    
    for group_start, group_end, group_value in groups:
        group_width = group_end - group_start + 1
        
        # Skip None/empty groups (padding columns)
        if group_value is None or str(group_value).strip() == '':
            # Still need to add placeholder nodes for empty columns
            for col in range(group_start, group_end + 1):
                index_node = IndexNode(None)
                index_tree.add_index(index_node)
            continue
        
        # Check if there are more meaningful rows below for this column group
        has_sub_structure = False
        if current_row < nrows:
            # Check if next row has different values within this column range
            next_row_groups = _detect_column_groups(schema_sheet, current_row + 1, group_start, group_end)
            # Sub-structure exists if next row has different values (more than 1 group, or different from parent)
            if len(next_row_groups) > 1:
                has_sub_structure = True
            elif len(next_row_groups) == 1:
                next_val = next_row_groups[0][2]
                if next_val is not None and str(next_val).strip() != '' and next_val != group_value:
                    has_sub_structure = True
        
        if has_sub_structure:
            # Recursively build sub-tree for this column group
            sub_index_tree = construct_index_tree_flattened(
                schema_sheet, 
                start_row=current_row + 1, 
                start_col=group_start, 
                end_col=group_end
            )
            # The sub-tree's root becomes a node with children
            index_node = IndexNode(group_value)
            for child in sub_index_tree.root.children:
                child.father = index_node
                index_node.add_child(child)
            index_tree.add_index(index_node)
        else:
            # No sub-structure - create final leaf node(s)
            if group_width == 1:
                # Single column - use the value from this row, but build path from all remaining rows
                path_parts = [str(group_value)]
                for r in range(current_row + 1, nrows + 1):
                    val = schema_sheet.cell(row=r, column=group_start).value
                    if val is not None and str(val).strip() != '' and str(val) != path_parts[-1]:
                        path_parts.append(str(val))
                leaf_value = "-".join(path_parts)
                index_node = IndexNode(leaf_value)
                index_tree.add_index(index_node)
            else:
                # Multiple columns with same value and no sub-structure
                # This shouldn't happen normally, but handle gracefully by creating individual leaves
                for col in range(group_start, group_end + 1):
                    path_parts = [str(group_value)] if group_value else []
                    for r in range(current_row + 1, nrows + 1):
                        val = schema_sheet.cell(row=r, column=col).value
                        if val is not None and str(val).strip() != '':
                            if not path_parts or str(val) != path_parts[-1]:
                                path_parts.append(str(val))
                    leaf_value = "-".join(path_parts) if path_parts else None
                    index_node = IndexNode(leaf_value)
                    index_tree.add_index(index_node)
    
    return index_tree
    
    return index_tree


def construct_index_tree_smart(schema_sheet):
    """Smart index tree construction that handles both merged and flattened sheets."""
    from utils.sheet_utils import get_merge_cell_size, single_cell, get_sub_sheet
    
    # Check if sheet has merge info
    if _has_merge_info(schema_sheet):
        # Use original merge-based construction
        return construct_index_tree(schema_sheet)
    else:
        # Use value-based construction for flattened sheets
        return construct_index_tree_flattened(schema_sheet)


def construct_body_tree_dfs(index_tree: IndexTree, data_sheet, x, y, depth):
    from utils.sheet_utils import (
        get_merge_cell_size,
        get_merge_cell_value,
        get_sub_sheet,
    )

    cell = data_sheet.cell(row=x, column=y)
    x1, y1, x2, y2 = get_merge_cell_size(data_sheet, cell.coordinate)

    value = get_merge_cell_value(data_sheet, cell.coordinate)
    root = BodyNode(value)
    root.x1 = x1
    root.x2 = x2
    root.y1 = y1
    root.y2 = y2
    index_tree.add_leaf_body_node_by_pos(root, depth)

    # Check if we've reached the rightmost column
    if y2 >= data_sheet.max_column:
        return root

    row = x1
    while row <= x2:
        cell = data_sheet.cell(row=row, column=y2 + 1)
        xx1, yy1, xx2, yy2 = get_merge_cell_size(data_sheet, cell.coordinate)

        # Check merge cell granularity changes
        if xx1 < x1:  # Already built by a parent scope — reuse
            if (
                depth + 1 < len(index_tree.leaf_nodes)
                and len(index_tree.leaf_nodes[depth + 1].body) > 0
            ):
                child = index_tree.leaf_nodes[depth + 1].body[-1]
                if child:
                    root.add_child(child)
                    child.add_father(root)
        else:
            body_node = construct_body_tree_dfs(
                index_tree, data_sheet, xx1, yy1, depth + 1
            )
            body_node.add_father(root)
            root.add_child(body_node)

        row += xx2 - xx1 + 1

    return root


def construct_body_tree(index_tree: IndexTree, data_sheet):
    """Build a BodyTree from the data sheet, linked to the IndexTree."""
    from utils.sheet_utils import (
        get_merge_cell_size,
        get_merge_cell_value,
        get_sub_sheet,
    )

    if data_sheet is None:
        return None, None

    nrows = data_sheet.max_row
    ncols = data_sheet.max_column

    body_tree = BodyTree()
    root = body_tree.root

    row = 1
    while row <= nrows:
        cell = data_sheet.cell(row=row, column=1)
        x1, y1, x2, y2 = get_merge_cell_size(data_sheet, cell.coordinate)

        body_node = construct_body_tree_dfs(index_tree, data_sheet, x1, y1, 0)
        body_node.add_father(root)
        root.add_child(body_node)

        row += x2 - x1 + 1

    return body_tree, index_tree


def construct_sheet(sheet):
    from utils.split_utils import split_schema_row

    schame_sheet, data_sheet = split_schema_row(sheet)

    # Use smart index tree construction that handles both merged and flattened sheets
    index_tree = construct_index_tree_smart(schame_sheet)

    body_tree, _ = construct_body_tree(index_tree, data_sheet)

    return FeatureTree(index_tree=index_tree, body_tree=body_tree)


def construct_feature_tree(tree_dict):

    logger.info(f"construct_feature_tree() Start to Process!")
    start_time = time.time()

    try:
        index_tree = IndexTree()
        body_tree = BodyTree()

        for index, body in tree_dict.items():
            if isinstance(body, dict):  # dict -> FeatureTree
                body_node = BodyNode(construct_feature_tree(body))
            elif isinstance(body, (str, int, float, list)) or body is None:  # string
                body_node = BodyNode(body)
            else:  # sheet -> FeatureTree
                body_node = BodyNode(construct_sheet(body))

            # link body tree and index tree
            index_node = IndexNode(value=index)
            index_node.body = [body_node]

            # construct index tree
            index_tree.add_index(index_node)
            # construct body tree
            body_tree.add_deep(body_node)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e, tree_dict)

    f_tree = FeatureTree(index_tree=index_tree, body_tree=body_tree)

    end_time = time.time()
    logger.info(f"construct_feature_tree() Process File Successfully!")
    logger.info(f"Cost time: {end_time - start_time} ")

    return f_tree
