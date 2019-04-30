import copy
import json
import random
import requests
import uuid

from IPython import embed


# Makes initial request to gather current Service Queue information
url = "https://qa-data.fusioncloud.rackspace.net/v1/fusionS3/find"
payload = {"collection": "clbservicequeue"}
headers = {"content-type": "application/json"}
r = requests.post(url, data=json.dumps(payload), headers=headers)
# Stores Service Queue information
sq = r.json()


reqs = []
tickets = []

scenarios = []


def create_ticket(sq, sqid):
    # Stores the Service Queue with a matching SQID
    squeue = [x for x in sq if sqid == x['sqid']]
    if len(squeue):
        squeue = squeue[0]
    else:
        print "Service Queue with ID {} could not be located!".format(sqid)
        print "Exiting run..."
        exit(0)

    # Selects a Queue ID at random from the list of queues in the current Service Queue
    qid = squeue['queueview'][0]['queue'][random.randint(0, len(squeue['queueview'][0]['queue'])-1)]

    # Selects a Support Team at random from the list of Support Teams in the current Service Queue
    support_team = squeue['queueview'][0]['teams'][random.randint(0, len(squeue['queueview'][0]['teams'])-1)]

    # Generates a unique Resource ID
    res_id = str(uuid.uuid4())

    # Stores relevant ticket information
    tickets.append([res_id, [[qid, support_team]]])

    # Typically CORE or ENCORE
    source = squeue['queueview'][0]['sourceSystem']

    # Stores name of the overall Service Queue
    name = squeue['queueview'][0]['name']

    # Stores difficulty level
    difficulty = squeue['difficultyLevel']

    # Stores default status of "new"
    status = "new"

    # Stores blank entry for default assignee
    assignee = ""

    # Base Template for the request payload
    temp = {
        "entry": {
            "@type": "http://www.w3.org/2005/Atom",
            "title": "Ticketing",
            "content": {
                "event": {
                    "@type": "http://docs.rackspace.com/core/event",
                    "id": "e53d007a-fc23-11e1-975c-cfa6b29bb817",
                    "version": "2",
                    "resourceId": res_id,
                    "eventTime": "2017-08-28T11:51:11Z",
                    "type": "UPDATE",
                    "dataCenter": "DFW1",
                    "region": "DFW",
                    "product": {
                        "@type": "http://docs.rackspace.com/event/ticketing/ticket",
                        "difficultyLevel": difficulty,
                        "serviceCode": "Ticketing",
                        "assignee": assignee,
                        "version": "1",
                        "resourceType": "TICKET",
                        "status": status,
                        "supportTeam": support_team,
                        "ticketUpdateTime": "2017-08-28T14:05:27.339Z",
                        "sourceSystem": source,
                        "queue": {
                            "id": qid,
                            "name": name
                        }
                    }
                }
            }
        }
    }
    # Store populated template in Requests list
    reqs.append(temp)
    
def assign_ticket(ticket, assignee):
    rid = ticket[0]

    # Retrieves list of requests, finding matches based on an RID, and selects the most recent of those requests to use as a template
    temp = copy.deepcopy([x for x in reqs if rid == x["entry"]["content"]["event"]["resourceId"]][-1])

    # Changes value of the assignee
    temp["entry"]["content"]["event"]["product"]["assignee"] = assignee

    # Adds modified request to list of requests
    reqs.append(temp)

def change_status(ticket, status):
    rid = ticket[0]

    # Retrieves list of requests, finding matches based on an RID, and selects the most recent of those requests to use as a template
    temp = copy.deepcopy([x for x in reqs if rid == x["entry"]["content"]["event"]["resourceId"]][-1])

    # Changes value of the status
    temp["entry"]["content"]["event"]["product"]["status"] = status

    # Adds modified request to list of requests
    reqs.append(temp)

def change_sq(ticket, sqid):
    #change_status(ticket, "new")
    # Clears the assignee field
    assign_ticket(ticket, "")
    squeue = [x for x in sq if sqid == x['sqid']][0]
    qid = squeue['queueview'][0]['queue'][random.randint(0, len(squeue['queueview'][0]['queue'])-1)]
    support_team = squeue['queueview'][0]['teams'][random.randint(0, len(squeue['queueview'][0]['teams'])-1)]
    source = squeue['queueview'][0]['sourceSystem']
    name = squeue['queueview'][0]['name']
    difficulty = squeue['difficultyLevel']

    temp = copy.deepcopy([x for x in reqs if ticket[0] == x["entry"]["content"]["event"]["resourceId"]][-1])
    temp["entry"]["content"]["event"]["product"]["queue"]["id"] = qid
    temp["entry"]["content"]["event"]["product"]["supportTeam"] = support_team
    temp["entry"]["content"]["event"]["product"]["sourceSystem"] = source
    temp["entry"]["content"]["event"]["product"]["queue"]["name"] = name
    temp["entry"]["content"]["event"]["product"]["difficultyLevel"] = difficulty
    [x for x in tickets if ticket[0] == x[0]][0][1].append([qid, support_team])
    reqs.append(temp)

def clear_ticket_lists(tickets, reqs):
    del tickets[:]
    del reqs[:]



# Holds Function "Quick" References
call_references = {
    "create": create_ticket,
    "assign": assign_ticket,
    "change service queue": change_sq,
    "change status": change_status
}

# Holds Ticket Name "Quick" References
ticket_references = {}
# Generates Ticket Names
for x in range(0, 99):
    ticket_references["ticket {:02d}".format(x+1)] = x

# Loads Scenario Sequencing File
sequences_file = open("calabrio-scenarios.json", "r")
scenario_sequences = json.loads(sequences_file.read())
sequences_file.close()


scen_seq_list = scenario_sequences.keys()
scen_seq_list.sort()
for scenario_sequence in scen_seq_list:
    scen_seq_num = scenario_sequence.split()[1]
    s = scenario_sequences[scenario_sequence]
    for sequence in s:
        param1 = sequence[1]
        if len(sequence) == 2:
            call_references[sequence[0]](sq, param1)
        else:
            param2 = sequence[2]
            ticket_ref = ticket_references[param1]
            call_references[sequence[0]](tickets[ticket_ref], param2)

    # Creates and stores ticket and request data
    temp_scenario = [copy.deepcopy(tickets), copy.deepcopy(reqs)]
    scenarios.append(temp_scenario)

    # Cleans up tickets and reqs
    clear_ticket_lists(tickets, reqs)

    # Writes Generated Scenario Data to JSON file
    fout = open("calabrio-scenario-gen2-{}.json".format(scen_seq_num), "w")
    fout.write(json.dumps(temp_scenario[1], indent=4, sort_keys=True))
    fout.close()

    # Print Ticket IDs by Scenario (During Processing)
    print "{} Ticket IDs:".format(scenario_sequence)
    for x in temp_scenario[0]:
        print x[0]
    print
print

# Print Ticket IDs by Scenario (Post-Processing)
i = 1
for scenario in scenarios:
    print "Scenario {:02d} Ticket IDs:".format(i)
    for ticket in scenario[0]:
        print ticket[0]
    print
    i += 1
print

# Print Ticket IDs with Queue ID and Support Team History by Scenario (Post-Processing)
i = 1
for scenario in scenarios:
    print "Scenario {:02d} Ticket Event Resource IDs with Queue ID and Support Team History:".format(i)
    for ticket in scenario[0]:
        print ticket
    print
    i += 1
print


embed()
