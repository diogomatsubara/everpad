import sys
sys.path.append('../..')
from PySide.QtGui import (
    QDialog, QIcon, QPixmap,
    QLabel, QVBoxLayout, QFrame,
    QMessageBox, QAction, QWidget,
    QListWidgetItem, QMenu, QInputDialog,
)
from PySide.QtCore import Slot, Qt, QPoint
from everpad.interface.management import Ui_Dialog
from everpad.interface.notebook import Ui_Notebook
from everpad.pad.tools import get_icon
from everpad.tools import get_provider, get_auth_token
from everpad.basetypes import Note, Notebook, Resource
from functools import partial


class Management(QDialog):
    """Management dialog"""

    def __init__(self, app, *args, **kwargs):
        QDialog.__init__(self, *args, **kwargs)
        self.app = app
        self.closed = False
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowIcon(get_icon())
        for delay in (5, 10, 15, 30):
            self.ui.syncDelayBox.addItem('%d minutes' % delay,
                userData=str(delay * 60 * 1000),
            )
        self.ui.syncDelayBox.addItem('One hour', userData='3600000')
        self.ui.syncDelayBox.addItem('Manual', userData='-1')
        active_index = self.ui.syncDelayBox.findData(str(
            self.app.provider.get_sync_delay(),
        ))
        self.ui.syncDelayBox.setCurrentIndex(active_index)
        self.ui.syncDelayBox.currentIndexChanged.connect(self.delay_changed)
        self.ui.tabWidget.currentChanged.connect(self.update_tabs)
        self.ui.createNotebook.clicked.connect(self.create_notebook)
        self.update_tabs()

    @Slot()
    def update_tabs(self):
        if get_auth_token():
            self.ui.authBtn.setText('Remove Authorisation')
            self.ui.notebookTab.setEnabled(True)
            self.init_notebooks()
        else:
            self.ui.authBtn.setText('Authorise')
            self.ui.notebookTab.setEnabled(Fale)

    @Slot(int)
    def delay_changed(self, index):
        self.app.provider.set_sync_delay(
            int(self.ui.syncDelayBox.itemData(index)),
        )


    def init_notebooks(self):
        frame = QFrame()
        layout = QVBoxLayout()
        frame.setLayout(layout)
        self.ui.scrollArea.setWidget(frame)
        for notebook_struct in self.app.provider.list_notebooks():
            notebook = Notebook.from_tuple(notebook_struct)
            count = self.app.provider.get_notebook_notes_count(notebook.id)
            widget = QWidget()
            menu = QMenu(self)
            menu.addAction(self.tr('Change Name'), Slot()(partial(
                self.change_notebook, notebook=notebook,
            )))
            action = menu.addAction(self.tr('Remove Notebook'), Slot()(partial(
                self.remove_notebook, notebook=notebook,
            )))
            action.setEnabled(False)
            widget.ui = Ui_Notebook()
            widget.ui.setupUi(widget)
            widget.ui.name.setText(notebook.name)
            widget.ui.content.setText(self.tr('Containts %d notes') % count)
            widget.ui.actionBtn.setIcon(QIcon.fromTheme('gtk-properties'))
            widget.setFixedHeight(50)
            layout.addWidget(widget)
            widget.ui.actionBtn.clicked.connect(Slot()(partial(
                self.show_notebook_menu,
                menu=menu, widget=widget,
            )))

    def show_notebook_menu(self, menu, widget):
        pos = widget.mapToGlobal(widget.ui.actionBtn.pos())
        pos.setY(pos.y() + widget.ui.actionBtn.geometry().height() / 2)
        pos.setX(pos.x() + widget.ui.actionBtn.geometry().width() / 2)
        menu.exec_(pos)

    def remove_notebook(self, notebook):
        msg = QMessageBox(
            QMessageBox.Critical,
            self.tr("You try to delete a notebook"),
            self.tr("Are you sure want to delete this notebook and notes in it?"),
            QMessageBox.Yes | QMessageBox.No
        )
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            self.app.provider.delete_notebook(notebook.id)
            self.app.send_notify(u'Notebook "%s" deleted!' % notebook.name)
            self.update_tabs()

    def change_notebook(self, notebook):
        name, status = self._notebook_new_name(
            self.tr('Change notebook name'), notebook.name,
        )
        if status:
            notebook.name = name
            self.app.provider.update_notebook(notebook.struct)
            self.app.send_notify(u'Notebook "%s" renamed!' % notebook.name)
            self.update_tabs()

    @Slot()
    def create_notebook(self):
        name, status = self._notebook_new_name(
            self.tr('Create new notebook'),
        )
        if status:
            self.app.provider.create_notebook(name)
            self.app.send_notify(u'Notebook "%s" created!' % name)
            self.update_tabs()

    def _notebook_new_name(self, title, exclude=''):
        names = map(lambda nb: Notebook.from_tuple(nb).name,
            self.app.provider.list_notebooks(),
        )
        try:
            names.remove(exclude)
        except ValueError:
            pass
        name, status = QInputDialog.getText(self, title,
            self.tr('Enter notebook name:'),
        )
        while name in names and status:
            name, status = QInputDialog.getText(self, title,
                self.tr('Notebook with this name already exist. Enter notebook name'),
            )
        return name, status

    def closeEvent(self, event):
        event.ignore()
        self.closed = True
        self.hide()
