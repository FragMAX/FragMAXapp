#
# strings accepted by PDB when doing group deposition
#

SALUTATIONS = [
    "Dr.",
    "Mr.",
    "Mrs.",
]

ROLES = [
    "investigator",
    "principal investigator/group leader",
    "responsible scientist",
]

ORGANIZATION_TYPES = [
    "academic",
    "commercial",
    "government",
    "other",
]


COUNTRIES = [
    "Afghanistan",
    "Aland Islands",
    "Albania",
    "Algeria",
    "American Samoa",
    "Andorra",
    "Angola",
    "Anguilla",
    "Antarctica",
    "Antigua And Barbuda",
    "Argentina",
    "Armenia",
    "Aruba",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahamas",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belgium",
    "Belize",
    "Benin",
    "Bermuda",
    "Bhutan",
    "Bolivia, Plurinational State Of",
    "Bonaire, Sint Eustatius And Saba",
    "Bosnia And Herzegovina",
    "Botswana",
    "Bouvet Island",
    "Brazil",
    "British Indian Ocean Territory",
    "Brunei Darussalam",
    "Bulgaria",
    "Burkina Faso",
    "Burundi",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Cape Verde",
    "Cayman Islands",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Christmas Island",
    "Cocos (Keeling) Islands",
    "Colombia",
    "Comoros",
    "Congo",
    "Congo, The Democratic Republic Of The",
    "Cook Islands",
    "Costa Rica",
    "Cote D'Ivoire",
    "Croatia",
    "Cuba",
    "Curacao",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Equatorial Guinea",
    "Eritrea",
    "Estonia",
    "Ethiopia",
    "Falkland Islands (Malvinas)",
    "Faroe Islands",
    "Fiji",
    "Finland",
    "France",
    "French Guiana",
    "French Polynesia",
    "French Southern Territories",
    "Gabon",
    "Gambia",
    "Georgia",
    "Germany",
    "Ghana",
    "Gibraltar",
    "Greece",
    "Greenland",
    "Grenada",
    "Guadeloupe",
    "Guam",
    "Guatemala",
    "Guernsey",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Heard Island And Mcdonald Islands",
    "Holy See (Vatican City State)",
    "Honduras",
    "Hong Kong",
    "Hungary",
    "Iceland",
    "India",
    "Indonesia",
    "Iran, Islamic Republic Of",
    "Iraq",
    "Ireland",
    "Isle Of Man",
    "Israel",
    "Italy",
    "Jamaica",
    "Japan",
    "Jersey",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kiribati",
    "Korea, Democratic People's Republic Of",
    "Korea, Republic Of",
    "Kuwait",
    "Kyrgyzstan",
    "Lao People's Democratic Republic",
    "Latvia",
    "Lebanon",
    "Lesotho",
    "Liberia",
    "Libya",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Macao",
    "Macedonia",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Maldives",
    "Mali",
    "Malta",
    "Marshall Islands",
    "Martinique",
    "Mauritania",
    "Mauritius",
    "Mayotte",
    "Mexico",
    "Micronesia, Federated States Of",
    "Moldova, Republic Of",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Montserrat",
    "Morocco",
    "Mozambique",
    "Myanmar",
    "Namibia",
    "Nauru",
    "Nepal",
    "Netherlands",
    "New Caledonia",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "Niue",
    "Norfolk Island",
    "Northern Mariana Islands",
    "Norway",
    "Oman",
    "Pakistan",
    "Palau",
    "Palestinian Territory",
    "Panama",
    "Papua New Guinea",
    "Paraguay",
    "Peru",
    "Philippines",
    "Pitcairn",
    "Poland",
    "Portugal",
    "Puerto Rico",
    "Qatar",
    "Reunion",
    "Romania",
    "Russian Federation",
    "Rwanda",
    "Saint Barthelemy",
    "Saint Helena, Ascension And Tristan Da Cunha",
    "Saint Kitts And Nevis",
    "Saint Lucia",
    "Saint Martin (French Part)",
    "Saint Pierre And Miquelon",
    "Saint Vincent And The Grenadines",
    "Samoa",
    "San Marino",
    "Sao Tome And Principe",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Singapore",
    "Sint Maarten (Dutch Part)",
    "Slovakia",
    "Slovenia",
    "Solomon Islands",
    "Somalia",
    "South Africa",
    "South Georgia And The South Sandwich Islands",
    "South Sudan",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Suriname",
    "Svalbard And Jan Mayen",
    "Swaziland",
    "Sweden",
    "Switzerland",
    "Syrian Arab Republic",
    "Taiwan",
    "Tajikistan",
    "Tanzania, United Republic Of",
    "Thailand",
    "Timor-Leste",
    "Togo",
    "Tokelau",
    "Tonga",
    "Trinidad And Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Turks And Caicos Islands",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "United States Minor Outlying Islands",
    "Uruguay",
    "Uzbekistan",
    "Vanuatu",
    "Venezuela, Bolivarian Republic Of",
    "Viet Nam",
    "Virgin Islands, British",
    "Virgin Islands, U.S.",
    "Wallis And Futuna",
    "Western Sahara",
    "Yemen",
    "Zambia",
    "Zimbabwe",
]

SEQUENCE_RELEASE = [
    "release now",
    "hold for release",
]

COORDINATES_RELEASE = [
    "release now",
    "hold for 4 weeks",
    "hold for 6 weeks",
    "hold for 8 weeks",
    "hold for 6 months",
    "hold for 1 year",
    "hold for publication",
]

FUNDING_ORGANIZATIONS = [
    "Not funded",
    "Other government",
    "Other private",
    "ATIP-Avenir",
    "Academia Sinica (Taiwan)",
    "Academy of Finland",
    "Accelerated Early staGe drug dIScovery (AEGIS)",
    "Adaptimmune Ltd",
    "Agence Nationale de Recherches Sur le Sida et les Hepatites Virales (ANRS)",
    "Agence Nationale de la Recherche (ANR)",
    "Agencia Nacional de Investigacion e Innovacion (ANII)",
    "Agencia Nacional de Promocion Cientifica y Tecnologica (FONCYT)",
    "Ake Wiberg Foundation",
    "Alexander von Humboldt Foundation",
    "Alzheimer Forschung Initiative e.V.",
    "Alzheimers Drug Discovery Foundation (ADDF)",
    "Alzheimers Research UK (ARUK)",
    "American Cancer Society",
    "American Epilepsy Society",
    "American Heart Association",
    "Amyloidosis Foundation",
    "Aprea Therapeutics AB",
    "Australian Research Council (ARC)",
    "Australian Science and Industry Endowment Fund (SIEF)",
    "Austrian Research Promotion Agency",
    "Austrian Science Fund",
    "Autonomous Community of Madrid",
    "Baden-Wuerttemberg-Stiftung",
    "Banting Postdoctoral Fellowships",
    "Bavarian State Ministry for Education, Culture, Science and Arts",
    "Belarusian Republican Foundation for Fundamental Research",
    "Belgian Foundation against Cancer",
    "Bill & Melinda Gates Foundation",
    "Biotechnology and Biological Sciences Research Council (BBSRC)",
    "Birkbeck College",
    "Bloodwise",
    "Board of Research in Nuclear Sciences (BRNS)",
    "Boehringer Ingelheim Fonds (BIF)",
    "Brazilian National Council for Scientific and Technological Development (CNPq)",
    "British Heart Foundation",
    "Brookhaven National Laboratory (BNL)",
    "Burroughs Wellcome Fund",
    "Business Finland",
    "CAMS Innovation Fund for Medical Sciences (CIFMS)",
    "CHDI Foundation",
    "CIFAR Azrieli Global Scholars",
    "CRDF Global",
    "Canada Excellence Research Chair Award",
    "Canada Foundation for Innovation",
    "Canada Research Chairs",
    "Canadian Glycomics Network (GLYCONET)",
    "Canadian Institute for Advanced Research (CIFAR)",
    "Canadian Institutes of Health Research (CIHR)",
    "Cancer Council WA",
    "Cancer Prevention and Research Institute of Texas (CPRIT)",
    "Cancer Research UK",
    "Cancer and Polio Research Fund",
    "CancerGenomiCs.nl",
    "Cancerfonden",
    "Carl Trygger Foundation",
    "Centre National de la Recherche Scientifique (CNRS)",
    "Chan Zuckerberg Initiative",
    "Childrens Discovery Institute of Washington University and St. Louis Childrens Hospital",
    "Chinese Academy of Sciences",
    "Chinese Scholarship Council",
    "Christian Doppler Forschungsgesellschaft",
    "Columbia Technology Ventures",
    "Comision Nacional Cientifica y Technologica (CONICYT)",
    "Commonwealth Scholarship Commission (United Kingdom)",
    "Comunidad de Madrid",
    "Consejo Nacional de Ciencia y Tecnologia (CONACYT)",
    "Consortia for HIV/AIDS Vaccine Development",
    "Coordination for the Improvement of Higher Education Personnel",
    "Council of Scientific & Industrial Research (CSIR)",
    "Croatian Science Foundation",
    "Crohns and Colitis Foundation",
    "Cystic Fibrosis Foundation",
    "Czech Academy of Sciences",
    "Czech Science Foundation",
    "DOC Fellowship of the Austrian Academy of Sciences",
    "Damon Runyon Cancer Research Foundation",
    "Danish Agency for Science Technology and Innovation",
    "Danish Council for Independent Research",
    "Danish National Research Foundation",
    "David and Lucile Packard Foundation",
    "Defence Science and Technology Laboratory (DSTL)",
    "Defense Threat Reduction Agency (DTRA)",
    "Dementia Research Institute (DRI)",
    "Department of Biotechnology (DBT, India)",
    "Department of Defense (DOD, United States)",
    "Department of Energy (DOE, United States)",
    "Department of Health & Human Services (HHS)",
    "Department of Science & Technology (DST, India)",
    "Dutch Kidney Foundation",
    "EIPOD fellowship under Marie Sklodowska-Curie Actions COFUND",
    "Elite Network of Bavaria",
    "Engineering and Physical Sciences Research Council",
    "Enterprise Ireland",
    "Estonian Research Council",
    "European Commission",
    "European Communitys Seventh Framework Programme",
    "European Institute of Chemistry and Biology (IECB)",
    "European Molecular Biology Organization (EMBO)",
    "European Regional Development Fund",
    "European Research Council (ERC)",
    "European Union (EU)",
    "F. Hoffmann-La Roche LTD",
    "Finnish Cultural Foundation",
    "Florence Instruct-ERIC Center",
    "Fondation ARC",
    "Fondazione CARIPLO",
    "Fonds National de la Recherche Scientifique (FNRS)",
    "Fonds de Recherche du Quebec - Nature et Technologies (FRQNT)",
    "Fonds de Recherche du Quebec - Sante (FRQS)",
    "Fonds de la Recherche Scientifique (FNRS)",
    "Foundation for Barnes-Jewish Hospital",
    "Foundation for Medical Research (France)",
    "Foundation for Polish Science",
    "Foundation for Science and Technology (FCT)",
    "French Alternative Energies and Atomic Energy Commission (CEA)",
    "French Infrastructure for Integrated Structural Biology (FRISBI)",
    "French League Against Cancer",
    "French Ministry of Armed Forces",
    "French Muscular Dystrophy Association",
    "French National Institute of Agricultural Research (INRAE)",
    "French National Research Agency",
    "Friedreichs Ataxia Research Alliance (FARA)",
    "Fundacao para a Ciencia e a Tecnologia",
    "Future Leader Fellowship",
    "GHR Foundation",
    "General Secretariat for Research and Technology (GSRT)",
    "Generalitat de Catalunya",
    "German Federal Ministry for Economic Affairs and Energy",
    "German Federal Ministry for Education and Research",
    "German Research Foundation (DFG)",
    "German-Israeli Foundation for Research and Development",
    "Global Challenges Research Fund",
    "Global Health Innovative Technology Fund",
    "Grant Agency of the Czech Republic",
    "Grenoble Alliance for Integrated Structural Cell Biology (GRAL)",
    "Grenoble Instruct-ERIC Center (ISBG)",
    "H2020 Marie Curie Actions of the European Commission",
    "Health Research Council (HRC)",
    "Health-Holland",
    "Hellenic Foundation for Research and Innovation (HFRI)",
    "Helmholtz Association",
    "Heritage Medical Research Institute",
    "Herman Frasch Foundation",
    "Hessian Ministry of Science, Higher Education and Art (HMWK)",
    "Higher Education Funding Council for England",
    "Howard Hughes Medical Institute (HHMI)",
    "Human Frontier Science Program (HFSP)",
    "Hungarian Academy of Sciences",
    "Hungarian Ministry of Finance",
    "Hungarian National Research, Development and Innovation Office",
    "Imperial College London",
    "Innosuisse",
    "Innovative Medicines Initiative",
    "Institut Laue-Langevin",
    "Institute for Integrative Biology of the Cell (I2BC)",
    "Institute of Chemical Physics Russian Academy of Science",
    "International AIDS Vaccine Initiative",
    "Irish Research Council",
    "Israel Ministry of Science and Technology",
    "Israel Science Foundation",
    "Italian Association for Cancer Research",
    "Italian Medicines Agency",
    "Italian Ministry of Education",
    "Italian Ministry of Health",
    "Italian National Research Council (CNR)",
    "Jack Ma Foundation",
    "Jane Coffin Childs (JCC) Fund",
    "Jane and Aatos Erkko Foundation",
    "Japan Agency for Medical Research and Development (AMED)",
    "Japan Science and Technology",
    "Japan Society for the Promotion of Science (JSPS)",
    "Joachim Herz Stiftung",
    "John Innes Foundation",
    "Joint Supercomputer Center of the Russian Academy of Sciences",
    "KU Leuven",
    "Kay Kendall Leukaemia Fund",
    "Kidney Research UK",
    "Knut and Alice Wallenberg Foundation",
    "LOreal-UNESCO",
    "La Caixa Foundation",
    "Laboratories of Excellence (LabEx)",
    "Leducq Foundation",
    "Leibniz Association",
    "Leukemia & Lymphoma Society",
    "Leverhulme Trust",
    "Louis-Jeantet Foundation",
    "Ludwig Institute for Cancer Research (LICR)",
    "Lundbeckfonden",
    "Lustgarten Foundation",
    "Marie Sklodowska-Curie Actions, FragNET ITN",
    "Marsden Fund",
    "Max Planck Society",
    "Medical Research Council (MRC, Canada)",
    "Medical Research Council (MRC, United Kingdom)",
    "Michael J. Fox Foundation",
    "Minas Gerais State Agency for Research and Development (FAPEMIG)",
    "Ministerio de Ciencia e Innovacion (MCIN)",
    "Ministero dell Universita e della Ricerca",
    "Ministry of Business, Innovation and Employment (New Zealand)",
    "Ministry of Economy and Competitiveness (MINECO)",
    "Ministry of Education (MoE, China)",
    "Ministry of Education (MoE, Czech Republic)",
    "Ministry of Education (MoE, Korea)",
    "Ministry of Education (MoE, Singapore)",
    "Ministry of Education and Science of the Russian Federation",
    "Ministry of Education, Culture, Sports, Science and Technology (Japan)",
    "Ministry of Education, Youth and Sports of the Czech Republic",
    "Ministry of Human Capacities",
    "Ministry of Science and Higher Education (Poland)",
    "Ministry of Science and Higher Education of the Russian Federation",
    "Ministry of Science and Technology (MoST, China)",
    "Ministry of Science and Technology (MoST, Taiwan)",
    "Ministry of Science, Education and Sports of the Republic of Croatia",
    "Ministry of Science, ICT and Future Planning (MSIP)",
    "Ministry of Science, Technology and Innovation (MOSTI, Malaysia)",
    "Mizutani Foundation for Glycoscience",
    "Molecular and Cell Biology and Postgenomic Technologies",
    "Monash University/ARC Centre of Excellence in Advanced Molecular Imaging Alliance",
    "Monash Warwick Alliance",
    "Montpellier University of Excellence (MUSE)",
    "NATO Science for Peace and Security Program",
    "National Aeronautic Space Administration (NASA, United States)",
    "National Authority for Scientific Research in Romania (ANCS)",
    "National Basic Research Program of China (973 Program)",
    "National Center for Genetic Engineering and Biotechnology (Thailand)",
    "National Center for Research and Development (Poland)",
    "National Fund for Scientific Research",
    "National Health and Medical Research Council (NHMRC, Australia)",
    "National Institute of Food and Agriculture (NIFA, United States)",
    "National Institutes of Health/Eunice Kennedy Shriver National Institute of Child Health & Human Development (NIH/NICHD)",  # noqa
    "National Institutes of Health/John E. Fogarty International Center (NIH/FIC)",
    "National Institutes of Health/National Cancer Institute (NIH/NCI)",
    "National Institutes of Health/National Center for Advancing Translational Sciences (NIH/NCATS)",
    "National Institutes of Health/National Center for Complementary and Integrative Health (NIH/NCCIH)",
    "National Institutes of Health/National Center for Research Resources (NIH/NCRR)",
    "National Institutes of Health/National Eye Institute (NIH/NEI)",
    "National Institutes of Health/National Heart, Lung, and Blood Institute (NIH/NHLBI)",
    "National Institutes of Health/National Human Genome Research Institute (NIH/NHGRI)",
    "National Institutes of Health/National Institute Of Allergy and Infectious Diseases (NIH/NIAID)",
    "National Institutes of Health/National Institute of Arthritis and Musculoskeletal and Skin Diseases (NIH/NIAMS)",
    "National Institutes of Health/National Institute of Biomedical Imaging and Bioengineering (NIH/NIBIB)",
    "National Institutes of Health/National Institute of Dental and Craniofacial Research (NIH/NIDCR)",
    "National Institutes of Health/National Institute of Diabetes and Digestive and Kidney Disease (NIH/NIDDK)",
    "National Institutes of Health/National Institute of Environmental Health Sciences (NIH/NIEHS)",
    "National Institutes of Health/National Institute of General Medical Sciences (NIH/NIGMS)",
    "National Institutes of Health/National Institute of Mental Health (NIH/NIMH)",
    "National Institutes of Health/National Institute of Neurological Disorders and Stroke (NIH/NINDS)",
    "National Institutes of Health/National Institute on Aging (NIH/NIA)",
    "National Institutes of Health/National Institute on Alcohol Abuse and Alcoholism (NIH/NIAAA)",
    "National Institutes of Health/National Institute on Deafness and Other Communication Disorders (NIH/NIDCD)",
    "National Institutes of Health/National Institute on Drug Abuse (NIH/NIDA)",
    "National Institutes of Health/National Institute on Minority Health and Health Disparities (NIH/NIMHD)",
    "National Institutes of Health/National Library of Medicine (NIH/NLM)",
    "National Institutes of Health/Office of the Director",
    "National Natural Science Foundation of China (NSFC)",
    "National Research Council (NRC, Argentina)",
    "National Research Development and Innovation Office (NKFIH)",
    "National Research Foundation (NRF, Korea)",
    "National Research Foundation (NRF, Singapore)",
    "National Research Foundation in South Africa",
    "National Science Council (NSC, Taiwan)",
    "National Science Foundation (NSF, China)",
    "National Science Foundation (NSF, United States)",
    "National Scientific and Technical Research Council (CONICET)",
    "National Virtual Biotechnology Laboratory (NVBL)",
    "Natural Environment Research Council (NERC)",
    "Natural Sciences and Engineering Research Council (NSERC, Canada)",
    "Netherlands Organisation for Scientific Research (NWO)",
    "New Energy and Industrial Technology Development Organization (NEDO)",
    "Norwegian Cancer Society",
    "Norwegian Research Council",
    "Novartis FreeNovation",
    "Novo Nordisk Foundation",
    "Obel Family Foundation",
    "Office of Naval Research (ONR)",
    "Oncode Institute",
    "Ontario Early Researcher Awards",
    "Ontario Institute for Cancer Research",
    "Ontario Ministry of Colleges and Universities",
    "Ontario Research Fund",
    "OpenPlant",
    "Partnership for Structural Biology (PSB)",
    "Pasteur Institute",
    "Polish National Science Centre",
    "Programa de Apoyo a Proyectos de Investigacion e Innovacion Tecnologica (PAPIIT)",
    "Promedica Siftung",
    "Qatar Foundation",
    "Queen Mary University of London",
    "Regione Lazio (Italy)",
    "Research Council of Lithuania",
    "Research Council of Norway",
    "Research Foundation - Flanders (FWO)",
    "Robert A. Welch Foundation",
    "Royal Society",
    "Royal Society of New Zealand",
    "Rural Development Administration",
    "Russian Foundation for Basic Research",
    "Russian Science Foundation",
    "Sao Paulo Research Foundation (FAPESP)",
    "Sarcoma UK",
    "Saudi Ministry of Education",
    "Science Foundation Ireland",
    "Science and Engineering Research Board (SERB)",
    "Science and Technology Funding Council",
    "Seneca Foundation",
    "Shirley Boyde Foundation",
    "Sigrid Juselius Foundation",
    "Simons Foundation",
    "Slovenian Research Agency",
    "Spanish Ministry of Economy and Competitiveness",
    "Spanish Ministry of Science, Innovation, and Universities",
    "Spanish National Research Council",
    "Spar Nord Foundation",
    "St. Petersburg State University",
    "Swedish Energy Agency",
    "Swedish Research Council",
    "Swiss Nanoscience Institute",
    "Swiss National Science Foundation",
    "Synchrotron Light Research Institute (SLRI)",
    "TESS Research Foundation",
    "Techical University of Denmark (DTU)",
    "Technology Agency of the Czech Republic",
    "The Carlsberg Foundation",
    "The Carnegie Trust for the Universities of Scotland",
    "The Comammox Research Platform",
    "The Francis Crick Institute",
    "The G. Harold and Leila Y. Mathers Foundation",
    "The Giovanni Armenise-Harvard Foundation",
    "The Hospital For Sick Children Foundation",
    "The Mark Foundation",
    "The Structural Genomics Consortium (SGC)",
    "The Swedish Foundation for Strategic Research",
    "The Thailand Research Fund (TRF)",
    "The University Grants Committee, Research Grants Council (RGC)",
    "The Yanmar Environmental Sustainability Support Association",
    "Tobacco-Related Disease Research Program (TRDRP)",
    "Tower Cancer Research Foundation",
    "Translational Therapeutics Accelerator (TRx)",
    "Tuberous Sclerosis Association",
    "UK Research and Innovation (UKRI)",
    "United States - Israel Binational Science Foundation (BSF)",
    "United States Department of Agriculture (USDA)",
    "Universite de Toulouse",
    "University and Research - University of Milan",
    "University of Bologna",
    "University of Cambridge",
    "University of Vienna Research Platform Comammox",
    "University of Warwick",
    "University of Zurich",
    "Velux Stiftung",
    "Vidyasirimedhi Institute of Science and Technology (VISTEC)",
    "Vienna Science and Technology Fund (WWTF)",
    "Vinnova",
    "Volkswagen Foundation",
    "W. M. Keck Foundation",
    "Walloon Excellence in Lifesciences & BIOtechnology (WELBIO)",
    "Welch Foundation",
    "Wellcome Trust",
    "Wenner-Gren Foundation",
    "Wolfson Foundation",
    "World Health Organization (WHO)",
    "Worldwide Cancer Research",
    "Yousef Jameel Scholarship",
]