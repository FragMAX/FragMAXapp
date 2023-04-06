from fragview.sites import plugin


class BeamlineInfo(plugin.BeamlineInfo):
    detector_type = "Hybrid pixel direct counting device"
    detector_pixel_size = "0.075 mm x 0.075 mm"
    focusing_optics = "KB Mirrors"
    monochrom_type = "Si(111)"
    beam_divergence = "6 μrad x 104 μrad"
    polarisation = "0.99˚"
