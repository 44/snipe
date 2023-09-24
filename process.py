import csv
import random
import os

class Participant(object):
    def __init__(self, name):
        self.name = name
        self.shots = []

    def add(self, value):
        self.shots.append(value)

def read_data_from_reader(reader):
    participants = []
    header = True
    for row in reader:
        if header:
            header = False
        else:
            handle = row[0]
            if handle == '':
                continue
            participants.append(Participant(handle))
            participants[-1].add(0)
            for i in range(len(row)):
                if i <= 3:
                    continue
                try:
                    val = int(row[i])
                    if val > 0:
                        participants[-1].add(val)
                except ValueError:
                    pass
    return participants

def download_and_read_data():
    import requests
    with requests.Session() as s:
        from local_adapter import LocalFileAdapter
        s.mount('file://', LocalFileAdapter())

        url = os.environ.get('WALKERS_URL', '')
        lfile = os.environ.get('WALKERS_FILE', 'test_data.csv')
        if url == '':
            import pathlib
            pathlib.Path(os.path.abspath(lfile)).as_uri()

        download = s.get('file:///home/au/w/inv/walks/something.csv')
        decoded_content = download.content.decode('utf-8')
        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        return read_data_from_reader(cr)

def simulate(ps):
    shifts = [0] * len(ps)
    for i in range(len(shifts)):
        shifts[i] = min(random.randint(0, 5), len(ps[i].shots) - 1)

    total = 0
    cur = 0
    for p in ps:
        shots = p.shots
        total += shots[-shifts[cur]]
        cur += 1

    return (total, shifts)

def str_shifts(ps, shifts):
    line = '['
    for i in range(len(ps)):
        value = ps[i].shots[-shifts[i]]
        if value == 0:
             continue
        line += ps[i].name + '=' + str(ps[i].shots[-shifts[i]]) + ' '
    return line + ']'

def typed_shifts(ps, shifts):
    result = {}
    for i in range(len(ps)):
        value = ps[i].shots[-shifts[i]]
        if value == 0:
             continue
        result[ps[i].name] = value
    return result

rounding_to = int(os.environ.get('WALKERS_ROUNDING', 25000))
threshold = int(os.environ.get('WALKERS_THRESHOLD', 750000))

def generate_result(participants, adjustment):
    result = { "records": {}, "optimizations": [], "totals": {}, "totals_adjusted": {} }
    total = 0
    for i in participants:
        result["records"][i.name] = max(i.shots)
        total += max(i.shots)
    result["totals"]["total"] = total
    result["totals"]["next"] = (int(total / rounding_to) + 1) * rounding_to
    result["totals"]["need"] = (int(total / rounding_to) + 1) * rounding_to - total
    result["totals_adjusted"]["total"] = total + adjustment
    result["totals_adjusted"]["next"] = (int((total + adjustment) / rounding_to) + 1) * rounding_to
    result["totals_adjusted"]["need"] = (int((total + adjustment) / rounding_to) + 1) * rounding_to - total - adjustment
    result["adjustment"] = 0
    return result

def find_best(participants):
    result = generate_result(participants, 0)

    best = rounding_to
    for i in range(1000000):
        total, shifts = simulate(participants)
        if total < threshold:
            continue
        remaining = rounding_to - total % rounding_to
        if remaining < best:
            best = remaining
            result["optimizations"].append({ "total": total, "shifts": typed_shifts(participants, shifts), "remaining": remaining, "milestone": (int(total / rounding_to) + 1) * rounding_to})
    return result

class Member(object):
    def __init__(self, p, idx):
        self.p = p
        self.idx = idx
        self.total = p.shots[idx]
    def mutate(self):
        if random.randint(0, 1) == 0:
            self.idx = max(0, self.idx - 1)
        else:
            self.idx = min(len(self.p.shots) - 1, self.idx + 1)
        self.total = self.p.shots[self.idx]

class Permutation(object):
    def __init__(self, ps, adjustment, at_least):
        self.ps = ps
        self.members = []
        self.total = 0
        self.adjustment = adjustment
        self.at_least = at_least
        for i in range(len(ps)):
            self.members.append(Member(ps[i], random.randint(0, len(ps[i].shots) - 1)))
            self.total += self.members[-1].total
    def clone(self):
        result = Permutation(self.ps, self.adjustment, self.at_least)
        for i in range(len(self.members)):
            result.members[i].idx = self.members[i].idx
            result.members[i].total = self.members[i].total
        result.total = self.total
        result.adjustment = self.adjustment
        result.at_least = self.at_least
        return result
    def mutate(self):
        to_mutate = random.randint(0, len(self.members) - 1)
        prev = self.members[to_mutate].total
        self.members[to_mutate].mutate()
        self.total += self.members[to_mutate].total - prev
    def score(self):
        if self.total + self.adjustment < threshold:
            return 1000000
        total =  (int( (self.total + self.adjustment) / rounding_to) + 1) * rounding_to - self.total - self.adjustment
        # TODO:
        if total < 50:
            return 1000000
        return total
    def target(self):
        return (int( (self.total + self.adjustment) / rounding_to) + 1) * rounding_to
    def __str__(self):
        total = sum([m.total for m in self.members])
        return str_shifts(self.ps, [m.idx for m in self.members]) + " -> " + str(total) + " + " + str(self.adjustment)
    def result(self):
        shifts = {}
        for m in self.members:
            shifts[m.p.name] = m.p.shots[m.idx]
        return {
            "total": sum([m.total for m in self.members]) + self.adjustment,
            "shifts": shifts,
            "remaining": self.score(),
            "milestone": self.target(),
        }


class Population(object):
    def __init__(self, ps, adjustment, at_least):
        self.ps = ps
        self.population = []
        self.adjustment = adjustment
        self.at_least = at_least
        for i in range(10000):
            self.population.append(Permutation(ps, adjustment, at_least))
    def mutate(self):
        for p in self.population:
            p.mutate()
    def evolve(self):
        self.population = sorted(self.population, key=lambda x: x.score())
        self.population = self.population[:5000]
        for i in range(5000):
            self.population.append(self.population[i].clone())

def find_best_genetic(participants, adjustment, at_least, generations):
    result = generate_result(participants, adjustment)
    result["adjustment"] = adjustment
    population = Population(participants, adjustment, at_least)
    for i in range(generations):
        population.mutate()
        population.evolve()
    already_printed = set()
    cnt = 0
    for p in population.population:
        target = p.target()
        score = p.score()
        if score == 1000000:
            continue
        if score < at_least:
            continue
        if (target, score) in already_printed:
            continue
        already_printed.add((target, score))
        result["optimizations"].append(p.result())
        cnt += 1
        if cnt > 10:
            break
    return result

if __name__ == '__main__':
    import sys
    print(find_best_genetic(download_and_read_data(), int(sys.argv[1]), 50, 100))
