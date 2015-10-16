#!/usr/bin/python

import os
import sys
import urllib
import argparse
from datetime import date, timedelta, datetime
from crate import client


def delta_month(date, months):
    return date + timedelta(months * 365 / 12)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s','--start', help='start date', required=True)
    parser.add_argument('-e','--end', help='end date', required=True)
    parser.add_argument('-H','--host', help='host', required=True)
    return parser.parse_args()

def alter_table(cur, number_of_replicas):
    try:
        cur.execute("""ALTER TABLE github SET (number_of_replicas=?)""", (number_of_replicas,))
        print("alter table to number_of_replicas={}".format(str(number_of_replicas)))
    except Exception as e:
        print("error on alter table \n {}".format(e))

def main():
    try:
        aws_secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
        aws_access_key = os.environ['AWS_ACCESS_KEY_ID']
    except KeyError:
        print("Please set your AWS_SECRET_ACCESS_KEY and AWS_ACCESS_KEY_ID environment variables.")
        return 1

    args = parse_args()

    start_date = datetime.strptime(args.start, "%Y/%m")
    end_date = datetime.strptime(args.end, "%Y/%m")

    connection = client.connect(args.host, error_trace=True)
    cur = connection.cursor()

    alter_table(cur, 0)

    for single_date in (start_date + timedelta(n) for n in range((delta_month(end_date, 1) - start_date).days)):
        import_data = single_date.strftime("%Y-%m-%d");
        month_partition = single_date.strftime("%Y-%m");

        print('Importing github data for {0} ...'.format(import_data))
        s3_url = 's3://{}:{}@crate.sampledata/github_archive/{}-*'.format(urllib.quote_plus(aws_access_key),
            urllib.quote_plus(aws_secret_key), import_data)
        cmd = '''COPY github PARTITION (month_partition=?) FROM ? WITH (bulk_size=1000, compression='gzip')'''
        try:
            cur.execute(cmd, (month_partition, s3_url,))
        except Exception as e:
            print("Error while importing {}: {}".format(import_data, e))
            print(e.error_trace)

    alter_table(cur, 1)
    return 0

if __name__=='__main__':
    sys.exit(main())

