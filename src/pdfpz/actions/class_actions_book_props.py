from pdfpz.core.class_book_manifest import PdfProps, BooksShelf
from pdfpz.core.class_tmp_path import TmpPath
from pdfpz.actions.class_book_manifest_file_actions import is_file

map_prop_field_to_tmppath_property = {
    "renamed": TmpPath.path_sanitized_renamed_tmp
}

map_prop_field_name_to_prop_field = {
    "renamed": PdfProps.renamed
}

               

class BookPropsActions:
    def __init__(self):
        self.pdf_props = None
        self.name = None
        self.id_book_table = None
    
    def set_name(self, name: str):
        self.name = name

    def set_id(self):
        self.id_book_table = None # TODO from DB
                   
    def set_props_from_db(self) -> None:
        """
        set PdfProps same values as DB 
        """
        self.pdf_props = None # TODO should be values from db 
    
    def save_props_to_db(self) -> None:
        """
        saver PdfProps to db 
        """
        self.pdf_props = None # TODO should be values from db 


            
    def set_props_from_filesystem(self):
        tmp_path: TmpPath = None
        for prop in map_prop_field_name_to_prop_field:
            fpath = tmp_path.__getattribute__(map_prop_field_to_tmppath_property) 
            file_exist = is_file(fpath) 
            self.pdf_props.__setattr__(name=map_prop_field_name_to_prop_field[prop]], value=file_exist ) 
    
    def set_props_from_filesystem_and_update_db(self):
        self.set_props_from_filesystem()
        # update db props table of book id    
        
        
class BooksPropsAction:
    def __init__(self, books_shelf:BooksShelf):
        props_act: BookPropsActions = BookPropsActions()
        self.book_shelf= books_shelf
        self.book_name: str = None
        # TODO iterate on books_shelf and get book name
        props_act.set_name(self.book_name)
        props_act.set_props_from_db()
        props_act.set_props_from_filesystem()
        props_act.save_props_to_db()      