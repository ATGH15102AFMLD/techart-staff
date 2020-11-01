# Description: IFileOperation wrapper to Copy, Move, Delete, Delete to Recycle
#     https://docs.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ifileoperation

# stdlib
from typing import List
from ctypes import c_ulong
# pywin32
import pythoncom
from win32com.shell import shell
from win32com.shell import shellcon


class Fo:
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"
    RECYCLE = "recycle"


def __create_shell_item_array(items: List[str]): # -> shell.PyIShellItemArray:
    pidls = []
    for it in items:
        it = it.replace('/', '\\')
        pidl = shell.SHParseDisplayName(it, 0, None)
        pidls.append(pidl[0])
    return shell.SHCreateShellItemArrayFromIDLists(pidls)


def __hr(hresult: int) -> int:
    return c_ulong(hresult).value


def file_operation(items: List[str], op: str, dst: str = "") -> bool:
    # create an instance of IShellItem for the destination folder
    destination = None
    if op in [Fo.COPY, Fo.MOVE]:
        dst = dst.replace('/', '\\')
        destination = shell.SHCreateItemFromParsingName(dst, None, shell.IID_IShellItem)
    # create IShellItemArray from items
    sia = __create_shell_item_array(items)
    # create an instance of IFileOperation
    fo = pythoncom.CoCreateInstance(shell.CLSID_FileOperation, None, pythoncom.CLSCTX_ALL, shell.IID_IFileOperation)
    # queue the operation
    op = op.lower()
    if op == Fo.COPY:
        fo.CopyItems(sia, destination)
    elif op == Fo.MOVE:
        fo.MoveItems(sia, destination)
    elif op == Fo.RECYCLE:
        fo.DeleteItems(sia)
    elif op == Fo.DELETE:
        # if SetOperationFlags is not called, the default value used by the operation
        # is FOF_ALLOWUNDO | FOF_NOCONFIRMMKDIR
        fo.SetOperationFlags(shellcon.FOF_NOCONFIRMMKDIR)
        fo.DeleteItems(sia)
    else:
        return False
    # commit
    try:
        fo.PerformOperations()
    except pythoncom.pywintypes.com_error as e:
        # COPYENGINE_E_USER_CANCELLED = 0x80270000 (-2144927744) - User canceled the current action
        if __hr(e.hresult) != shellcon.COPYENGINE_E_USER_CANCELLED:
            print(e, flush=True)

    return True
