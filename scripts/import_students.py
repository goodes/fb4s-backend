from beeprint import pp
import csv, codecs, cStringIO
import rethinkdb as r


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

def connect_and_create():
    r.connect('rtdb.goodes.net').repl()
    if 'fb4s' not in r.db_list().run():
        r.db_create('fb4s').run()
    db = r.db('fb4s')
    if 'students' not in db.table_list().run():
        db.table_create('students').run()
    return db.table('students')


def import_students(table, path):
    if len(list(table.run())) > 0:
        print "Table not empty"
        return

    with open(path) as fp:
        csvfile = UTF8Recoder(fp, 'utf-8')
        for r in csv.DictReader(csvfile):
            # r['name'] = unicode(r['name'].decode('utf-8')
            r['name'] = r['name'].strip()
            r['address'] = r['address'].strip()
            r['id'] = int(r['id'].strip())
            pp(r)
            table.insert(r).run()

if __name__ == "__main__":
    table = connect_and_create()
    import_students(table, path="../../students.csv/Sheet1-Table 1.csv")
