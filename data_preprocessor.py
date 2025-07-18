import re
import json
from collections import defaultdict

import re
from collections import defaultdict
import json

import re
import json
from collections import defaultdict

def clean_and_structure(raw_text: str):
    entries = []
    interviews = re.split(r'## Interview Preparation Journey', raw_text)
    
    for interview in interviews:
        if not interview.strip():
            continue
        
        data = defaultdict(lambda: None)
        # Extract application method
        match = re.search(r'Application process\nWhere: (.+)', interview)
        if match:
            data['application_method'] = match.group(1).strip()
        
        # Extract eligibility
        match = re.search(r'Eligibility: ([^\n]+)', interview)
        if match:
            data['eligibility'] = match.group(1).strip()

        # Extract preparation duration
        match = re.search(r'Preparation\nDuration: ([^\n]+)', interview)
        if match:
            data['preparation_duration'] = match.group(1).strip()

        # Extract preparation topics
        match = re.search(r'Topics: ([^\n]+)', interview)
        if match:
            data['topics'] = [topic.strip() for topic in match.group(1).split(',')]

        # Extract tips
        tips = re.findall(r'Tip \d+: (.+)', interview)
        if tips:
            data['tips'] = tips

        # Extract resume tips
        resume_tips = re.findall(r'Resume tip\n(?:Tip \d+: )?(.+?)(?=\n(?:Tip \d+:|$))', interview, flags=re.DOTALL)
        if resume_tips:
            data['resume_tips'] = [tip.strip().replace('\n', ' ') for tip in resume_tips]

        # Extract rounds
        rounds = []
        round_blocks = re.findall(r'### Round (\d+)(.+?)(?=### Round \d+|$)', interview, flags=re.DOTALL)
        for round_num, round_text in round_blocks:
            round_info = {
                'round_number': int(round_num),
                'mode': re.search(r'Mode[:\s]*([^\n]+)', round_text, re.IGNORECASE),
                'duration': re.search(r'Duration[:\s]*([^\n]+)', round_text, re.IGNORECASE),
                'type': None,
                'questions': []
            }

            # Parse questions inside each round
            questions = re.findall(r'\d+\.\s+(.+?)\n(?:Easy|Moderate|Hard)', round_text)
            difficulties = re.findall(r'\d+\.\s+.+?\n(Easy|Moderate|Hard)', round_text)
            approaches = re.findall(r'Problem approach\n(.+?)(?=\nSolve later|\n\d+\.\s|$)', round_text, re.DOTALL)

            for i in range(len(questions)):
                q = {
                    'title': questions[i].strip(),
                    'difficulty': difficulties[i].strip() if i < len(difficulties) else 'Unknown',
                    'approach': approaches[i].strip().replace('\n', ' ') if i < len(approaches) else ''
                }
                round_info['questions'].append(q)

            rounds.append(round_info)

        data['interview_rounds'] = rounds
        entries.append(dict(data))

    return entries

def json_to_documents(json_data):
    """
    Converts structured interview JSON data into detailed human-readable documents.
    Supports full interview round details, coding/system/puzzle questions, and links.
    """
    documents = []

    for entry in json_data:
        lines = []

        # Optional Header
        company = entry.get("company")
        role = entry.get("role")
        if company or role:
            header = []
            if company:
                header.append(f"Company: {company}")
            if role:
                header.append(f"Role: {role}")
            lines.append(" | ".join(header))

        # Basic Info
        lines.append(f"Application Method: {entry.get('application_method', 'N/A')}")
        lines.append(f"Eligibility: {entry.get('eligibility', 'N/A')}")
        lines.append(f"Preparation Duration: {entry.get('preparation_duration', 'N/A')}")
        topics = entry.get('topics', [])
        lines.append(f"Topics Covered: {', '.join(topics) if topics else 'N/A'}")

        # General Tips
        tips = entry.get("tips", [])
        if tips:
            lines.append("\nGeneral Tips:")
            for tip in tips:
                lines.append(f"- {tip}")

        # Resume Tips
        resume_tips = entry.get("resume_tips", [])
        if resume_tips:
            lines.append("\nResume Tips:")
            for tip in resume_tips:
                lines.append(f"- {tip}")

        # Interview Rounds
        rounds = entry.get("interview_rounds", [])
        if rounds:
            lines.append("\nInterview Rounds:")

        for r in rounds:
            rnum = r.get("round_number", "N/A")
            mode = r.get("mode", "N/A")
            duration = r.get("duration", "N/A")
            interview_date = r.get("interview_date", "N/A")

            lines.append(f"\nRound {rnum} | Mode: {mode} | Duration: {duration} | Date: {interview_date}")

            # Questions
            questions = r.get("questions", [])
            if questions:
                lines.append("Questions:")
                for i, q in enumerate(questions, 1):
                    title = q.get("title", f"Question {i}")
                    difficulty = q.get("difficulty", "N/A")
                    approach = q.get("approach", "N/A")
                    link = q.get("try_link", "")

                    lines.append(f"  • {title} ({difficulty})" if difficulty != "N/A" else f"  • {title}")
                    if approach:
                        lines.append(f"    Approach: {approach}")
                    if link:
                        lines.append(f"    Link: {link}")
            else:
                lines.append("  No questions listed.")

            # System Design Question (if present)
            sdq = r.get("system_design_question")
            if sdq and sdq.get("question"):
                lines.append("System Design Question:")
                lines.append(f"  Question: {sdq['question']}")
                if sdq.get("approach"):
                    lines.append(f"  Approach: {sdq['approach']}")

            # Round-level links (if exist in raw)
            raw_text = entry.get("raw", "")
            round_number_str = f"### Round {rnum}"
            if round_number_str in raw_text:
                round_text = raw_text.split(round_number_str, 1)[1].split("### Round", 1)[0]
                links_match = re.findall(r"https?://[^\s,\)]+", round_text)
                if links_match:
                    lines.append("  Links:")
                    for l in links_match:
                        lines.append(f"    - {l}")

        documents.append("\n".join(lines).strip())

    return documents

