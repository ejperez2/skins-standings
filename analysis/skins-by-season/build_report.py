"""Injects skins_data.json into skins_report_template.html -> skins_report.html."""
import os
here=os.path.dirname(os.path.abspath(__file__))
t=open(os.path.join(here,"skins_report_template.html")).read()
open(os.path.join(here,"skins_report.html"),"w").write(t.replace("__DATA__",open(os.path.join(here,"skins_data.json")).read()))
