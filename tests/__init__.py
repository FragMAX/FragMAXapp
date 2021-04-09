#
# include modules that we have no tests for yet,
# so they show up in the coverage
#

import fragview.management.commands.adduser  # noqa F401
import fragview.management.commands.gettoken  # noqa F401
import fragview.management.commands.getfrags  # noqa F401
import fragview.management.commands.update  # noqa F401
import fragview.cbf  # noqa F401
import fragview.sites.hzb  # noqa F401
import fragview.scraper.dials  # noqa F401
import fragview.scraper.dimple  # noqa F401
import fragview.scraper.fspipeline  # noqa F401
import fragview.scraper.edna  # noqa F401
import fragview.scraper.proc_logs  # noqa F401
import fragview.scraper.xds  # noqa F401
import fragview.scraper.xdsapp  # noqa F401
import jobs.jobsd.local  # noqa F401
import jobs.jobsd.slurm  # noqa F401
