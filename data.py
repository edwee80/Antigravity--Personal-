"""
RESUME CONFIGURATION DATA (PYTHON) - MUHAMMAD EDREY BIN JEFFREY

Contains authenticated resume information based on official academic,
internship, and project records.
"""

from typing import Dict, List, Any

RESUME_DATA: Dict[str, Any] = {
    "personal": {
        "name": "Muhammad Edrey",
        "last_name": "Bin Jeffrey",
        "full_name": "Muhammad Edrey Bin Jeffrey",
        "title": "Civil Engineering Undergraduate",
        "license_badge": "B.Eng (Civil Engineering) @ NUS",
        "tagline": "Specialisation in Digitalisation in Urban Infrastructure",
        "location": "Singapore",
        "email": "edreyjeffrey@gmail.com",
        "phone": "+65 8138 3602",
        "linkedin": "https://www.linkedin.com/in/edreyjeffrey2311/",
        "portfolio": "https://www.linkedin.com/in/edreyjeffrey2311/",
        "availability": "Available for Civil Engineering Internships & Projects",
        "summary": (
            "Civil Engineering undergraduate at the National University of Singapore (NUS) specialising "
            "in the Digitalisation in Urban Infrastructure. Graduated with Diploma in "
            "Civil Engineering from Singapore Polytechnic (SP) with academic distinctions across "
            "Computer Aided Drafting (CAD), Structural Mechanics, Geomatics, and Project Management. Hands-on experience "
            "conducting structural inspections of condominiums and hotels, material testing for concrete "
            "and cement, and digital modeling using Autodesk Robot Structural Analysis, AutoCAD, and Revit."
        ),
    },

    "metrics": [
        {
            "value": "4.11 / 5.0",
            "label": "NUS B.Eng (Civil Engineering) GPA",
            "detail": "Specialisation in Digitalisation in Urban Infrastructure",
        },
        {
            "value": "3.92 / 4.0",
            "label": "SP Diploma in Civil Engineering GPA",
            "detail": "Graduated with Diploma in Civil Engineering (with Merit)",
        },
    ],

    "skill_categories": [
        {
            "category": "Drafting, Modeling & Structural Analysis",
            "icon": "cpu",
            "skills": [
                {"name": "AutoCAD Drafting", "level": 94},
                {"name": "Autodesk Revit (BIM)", "level": 90},
                {"name": "Autodesk Robot Structural Analysis", "level": 88},
                {"name": "Structural Mechanics & Detailing", "level": 92},
            ],
        },
        {
            "category": "Field Engineering, Materials & Inspection",
            "icon": "building",
            "skills": [
                {"name": "Structural Condition Inspection", "level": 95},
                {"name": "Concrete & Cement Material Testing", "level": 94},
                {"name": "Geomatics & Engineering Surveying", "level": 90},
                {"name": "Steel Fibre Reinforced Concrete (SFRC)", "level": 92},
            ],
        },
        {
            "category": "Project Controls, Leadership & Reporting",
            "icon": "clipboard",
            "skills": [
                {"name": "Technical Inspection Reporting", "level": 96},
                {"name": "Project Proposal & Safety Documentation", "level": 92},
                {"name": "Microsoft Excel & Data Processing", "level": 90},
                {"name": "Engineering Mathematics", "level": 94},
            ],
        },
    ],

    "projects": [
        {
            "id": "sfrc-tidal-durability",
            "title": "Durability Study of Steel Fibre Reinforced Concrete in Tidal Zone",
            "category": "Research & Materials",
            "type": "Integrated Capstone Project",
            "budget": "Academic Distinction",
            "year": "2022 - 2023",
            "role": "Lead Student Researcher",
            "summary": "Comprehensive experimental investigation evaluating the durability, mechanical behaviour, and crack propagation resistance of Steel Fibre Reinforced Concrete (SFRC) under severe marine tidal conditions.",
            "highlights": [
                "Subjected SFRC test specimens to cyclic tidal wetting and drying to simulate aggressive coastal micro-climates.",
                "Analyzed compressive strength, tensile crack bridging, and permeability against standard concrete mixes.",
                "Authored extensive technical research report and presented experimental findings, earning an Academic Distinction for the Integrated Project at Singapore Polytechnic.",
            ],
            "tools": ["Concrete Testing", "Material Characterization", "Structural Mechanics", "Technical Reporting", "Excel"],
            "stats": {"Environment": "Marine Tidal Zone", "Material": "Steel Fibre (SFRC)", "Academic Result": "Distinction"},
        },
        {
            "id": "mse-structural-inspections",
            "title": "High-Density Residential & Commercial Hotel Structural Inspection",
            "category": "Inspection & Field",
            "type": "Consulting Engineering Inspection",
            "budget": "Client Deliverable",
            "year": "2021 & 2023",
            "role": "Part-Time Assistant Engineer",
            "summary": "Conducted comprehensive on-site structural condition inspections across a major 300-unit condominium estate and an under-construction commercial hotel in Singapore.",
            "highlights": [
                "Performed systematic structural inspections evaluating columns, beams, load-bearing elements, and finishes for defects and compliance.",
                "Synthesized site observations, measurements, and photographic evidence into formal Inspection Reports submitted directly to clients.",
                "Coordinated with project stakeholders to ensure alignment with Singapore building regulations and approved construction drawings.",
            ],
            "tools": ["Structural Inspection", "Technical Reporting", "Defect Assessment", "Site Review"],
            "stats": {"Residential": "300-Unit Condo", "Commercial": "Hotel Under Construction", "Outcome": "Client Reports Submitted"},
        },
        {
            "id": "digitalisation-urban-infra",
            "title": "Digitalisation of Urban Infrastructure Modeling & BIM",
            "category": "BIM & Digital",
            "type": "Academic Specialisation",
            "budget": "NUS Engineering",
            "year": "2025 - Present",
            "role": "B.Eng Candidate",
            "summary": "Advanced structural modeling, computational analysis, and digital integration applied to high-density modern urban infrastructure systems.",
            "highlights": [
                "Developed detailed 3D structural and architectural models utilizing Autodesk Revit (BIM) and AutoCAD.",
                "Conducted computational structural analysis utilizing Autodesk Robot Structural Analysis to verify member stresses and load distribution.",
                "Explored smart infrastructure workflows and digital twin applications for sustainable urban construction.",
            ],
            "tools": ["Autodesk Robot", "Autodesk Revit", "AutoCAD", "BIM Workflows", "Urban Infrastructure"],
            "stats": {"Specialisation": "Urban Digitalisation", "Institution": "NUS", "Current GPA": "4.11 / 5.00"},
        },
        {
            "id": "nus-leadership-governance",
            "title": "CESE Orientation Camp & NUSMS Rihlah Project Direction",
            "category": "Project Management",
            "type": "Committee Leadership & Operations",
            "budget": "NUS Student Affairs",
            "year": "2025 - Present",
            "role": "Project Director / Vice Project Director",
            "summary": "Strategic leadership, budgeting, logistics coordination, and safety documentation for major university orientation and sports wellness programmes.",
            "highlights": [
                "Led multi-disciplinary committees as Project Director for Rihlah (Sports & Wellness Ad-hoc), directing programming, finance, logistics, and publicity.",
                "Co-directed the NUS CESE Camp for incoming Civil and Environmental Engineering students, authoring project proposals, budgets, and safety plans.",
                "Appointed as Senior Advisor (Aug 2026 – Present) to mentor incoming project directors and advise on executive committee management.",
            ],
            "tools": ["Project Management", "Safety Documentation", "Proposal Writing", "Financial Budgeting", "Team Leadership"],
            "stats": {"Ad-hoc Roles": "Project Director / Vice Director", "Current Role": "Senior Advisor", "Impact": "100+ Students"},
        },
    ],

    "experience": [
        {
            "role": "Part-Time Assistant Engineer",
            "company": "MSE Consultants Pte Ltd",
            "location": "Singapore",
            "period": "Sep 2021 & Mar 2023",
            "type": "Part-time",
            "achievements": [
                "Conducted thorough structural inspections of a 300-unit condominium estate and an under-construction commercial hotel.",
                "Authored detailed Inspection Reports outlining structural integrity assessments, non-conformances, and recommendations for client submission.",
                "Assisted consulting engineers with on-site defect surveys, concrete quality verifications, and compliance checks against construction drawings.",
            ],
        },
        {
            "role": "Civil Engineering Intern",
            "company": "RAK Materials Consultants Pte Ltd",
            "location": "Singapore",
            "period": "Mar 2022 – Aug 2022",
            "type": "Internship",
            "achievements": [
                "Assisted in carrying out standard laboratory and field Material Testing on concrete and cement specimens.",
                "Drafted and finalized Test Results Reports detailing compliance with Singapore and international testing benchmarks for submission to clients.",
                "Maintained strict quality control protocols during sample curing, slump testing, and compressive cube crushing tests.",
            ],
        },
        {
            "role": "Senior Advisor (Aug 2026 – Present) / Project Director (Aug 2025 – Jul 2026)",
            "company": "NUS Muslim Society (NUSMS)",
            "location": "National University of Singapore",
            "period": "Aug 2025 – Present",
            "type": "Co-Curricular Leadership",
            "achievements": [
                "Serve as Senior Advisor for Rihlah (Sports and Wellness Ad-hoc), guiding Project Directors in strategic planning and committee governance.",
                "Spearheaded the Rihlah committee as Project Director, overseeing end-to-end programme execution, financial budgeting, welfare, logistics, and marketing.",
                "Fostered cross-subcommittee synergy to execute safe and successful community engagement initiatives.",
            ],
        },
        {
            "role": "Vice Project Director",
            "company": "NUS Civil Engineering (NUS CESE Camp)",
            "location": "National University of Singapore",
            "period": "Aug 2025 – Jul 2026",
            "type": "Co-Curricular Leadership",
            "achievements": [
                "Served on the executive committee for NUS CESE Camp, an orientation camp organized for incoming Civil and Environmental Engineering freshmen.",
                "Led and mentored committee members, establishing task milestones and operational schedules.",
                "Collaborated closely with the Project Director on the formal Project Proposal, resource logistics, and comprehensive campus Safety Documentations.",
            ],
        },
    ],

    "education": [
        {
            "degree": "Bachelor of Engineering (Civil Engineering)",
            "institution": "National University of Singapore (NUS)",
            "period": "Aug 2025 – Present",
            "highlights": "Specialisation in Digitalisation of Urban Infrastructure. Current GPA: 4.11 / 5.00. Activities: NUS Muslim Society (Senior Advisor & Project Director), NUS CESE Camp (Vice Project Director).",
        },
        {
            "degree": "Diploma in Civil Engineering",
            "institution": "Singapore Polytechnic (SP)",
            "period": "Apr 2020 – Apr 2023",
            "highlights": "GPA: 3.92 / 4.00. Distinctions in: Computer Aided Drafting, Structural Mechanics, Geomatics, Engineering Mathematics, Project Management, Integrated Project. Integrated Project: Durability Study of Steel Fibre Reinforced Concrete in Tidal Zone. Activities: SP Football.",
        },
    ],

    "certifications": [
        {
            "title": "Distinction in Computer Aided Drafting & Structural Mechanics",
            "issuer": "Singapore Polytechnic",
            "year": "Academic Distinction",
            "badge": "Distinction",
        },
        {
            "title": "Distinction in Geomatics & Engineering Mathematics",
            "issuer": "Singapore Polytechnic",
            "year": "Academic Distinction",
            "badge": "Distinction",
        },
        {
            "title": "Distinction in Project Management & Integrated Project",
            "issuer": "Singapore Polytechnic",
            "year": "Academic Distinction",
            "badge": "Distinction",
        },
        {
            "title": "Specialisation in Digitalisation of Urban Infrastructure",
            "issuer": "National University of Singapore (NUS)",
            "year": "Undergraduate Specialisation",
            "badge": "NUS Specialisation",
        },
    ],
}
