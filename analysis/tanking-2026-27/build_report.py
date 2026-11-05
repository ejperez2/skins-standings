"""Injects report_data.json into report_template.html -> report.html."""
import os
here=os.path.dirname(os.path.abspath(__file__))
t=open(os.path.join(here,"report_template.html")).read()
d=open(os.path.join(here,"report_data.json")).read()
open(os.path.join(here,"report.html"),"w").write(t.replace("__DATA__",d))
