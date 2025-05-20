import uuid

from a2a.types import Artifact, Part, TextPart


def new_artifact(
    parts: list[Part], name: str, description: str = ''
) -> Artifact:
    return Artifact(
        artifactId=str(uuid.uuid4()),
        parts=parts,
        name=name,
        description=description,
    )

def new_text_artifact(
    name: str,
    text: str,
    description: str = '',
) -> Artifact:
    return new_artifact(
        [Part(root=TextPart(text=text))], name, description,
    )

def new_data_artifact(
    name: str,
    data: dict[str, any],
    description: str = '',
):
    return new_artifact(
        [Part(root=DataPart(data=data))], name, description,
    )
