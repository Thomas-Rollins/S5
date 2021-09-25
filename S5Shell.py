import os

class s5shell:
    
    local_wDir = os.getcwd()
    cloud_cur_bucket = '/'
    cloud_wDir = ''

    def do_exit(self, args):
        return 0

    def do_quit(self, args):
        return 0

    def do_lc_copy(self, args):
        pass
        
    def do_cl_copy(self, args):
        pass

    def do_create_bucket(self, args):
       pass

    def do_create_folder(self, args):
        pass

    def do_ch_folder(self, args):
        pass

    def do_cwf(self, args):
        pass

    def do_list(self, args):
        pass

    def do_ccopy(self, args):
        pass

    def do_cdelete(self, args):
        pass
        
    def do_delete_bucket(self, args):
        pass

    def get_abs_local_path(self, path):
        if os.path.isabs(path):
            return path
        # case 1b <relative path>
        elif os.path.exists(os.path.normpath(os.path.join(self.local_wDir, path))):
            return os.path.normpath(os.path.join(self.local_wDir, path))
        else:
            return None