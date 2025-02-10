def process_participant_data(participant_data):
    """Process participant data from ODK repeat groups"""
    processed_data = []
    
    for p in participant_data.get('repeatPP', []):
        participant = {
            'first_name': p.get('repeatPP/firstNamePP', '').strip(),
            'surname': p.get('repeatPP/surNamePP', '').strip(),
            'gender': p.get('repeatPP/genderPP', ''),
            'phone_number': p.get('repeatPP/phoneNrPP', None),
            'own_phone': p.get('repeatPP/ownPhonePP', '') == 'yes',
            'crops': p.get('repeatPP/cropsPP', ''),
        }
        processed_data.append(participant)
    
    return processed_data

##############################
def process_participant_groups(event_data):
    """Process participant group data from different ODK forms"""
    groups = []
    
    # Handle AKILIMO events format
    if 'participantRepeat' in event_data:
        for group in event_data['participantRepeat']:
            groups.append({
                'participant_type': group.get('participantRepeat/participant', ''),
                'male_count': int(group.get('participantRepeat/participant_male', 0)),
                'female_count': int(group.get('participantRepeat/participant_female', 0))
            })
            
    # Handle dissemination events format
    elif 'participantDetails' in event_data:
        for group in event_data['participantDetails']:
            groups.append({
                'participant_type': group.get('participantDetails/participant', ''),
                'male_count': int(group.get('participantDetails/participant_male', 0)),
                'female_count': int(group.get('participantDetails/participant_female', 0))
            })
            
    return groups


##################

